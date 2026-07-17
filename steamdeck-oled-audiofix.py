import os, sys, io, tarfile, shutil, urllib, subprocess
from urllib.request import (urlretrieve as uRet, urlopen as uOpen, Request)

# vars
repo       = "https://steamdeck-packages.steamos.cloud/archlinux-mirror/jupiter-main/os/x86_64/"
repo_db    = "jupiter-main.db.tar.xz"
workdir    = "/tmp"
pkgstart   = "steamdeck-dsp-"
extractdir = "STEAMDECK_DSP_PKG"

dsp_pkg_items = [
    "usr/lib/firmware/amd/sof/",
    "usr/lib/firmware/amd/sof-tplg/",
    "usr/share/alsa/ucm2/"
]

class misc:
    @staticmethod
    def starttxt(): 
        os.system("clear")
        print("[-] steam deck oled audio fix (for non-steamos-based distros)")
        print("[-] this script is designed to grab missing (sof) firmware files and (alsa-ucm-conf) sound hardware rules")
        
    @staticmethod
    def checksys():
        system = os.uname().sysname
        if system != "Linux":
            print(f"[x] YOU NEED TO BE USING LINUX NOT WHATEVER THIS GARBAGE IS")
            sys.exit(1)
            
        kernel = os.uname().release
        ver = tuple(int(v) for v in os.uname().release.split(".")[:2])
        if ver < (7, 1) and not "valve" in kernel:
            print(f"[X] so it doesn't look like you're running a version of linux with valve's patches or version 7.1 or newer. im turning you away. come back with a supported kernel")
            sys.exit(1)
            
    @staticmethod
    def getroot():
        if os.geteuid() != 0:
            while True:
                misc.starttxt()
                print("[!] root privileges missing")
                print("[-] this script needs root privileges to copy the firmware files and alsa rules.")
                root_prompt = input("[?] rerun as sudo? [Y/n] ").lower()
                if root_prompt == "n":
                    print("[.] fine. your (hearing) loss")
                    sys.exit(1)
                elif root_prompt == "y":
                    os.execvp("sudo", ["sudo", sys.executable] + sys.argv)
        else:
            misc.starttxt()
            print("[+] running as root")
            
    @staticmethod 
    def parseargs():
        global workdir
        for arg in sys.argv[1:]:
            if arg.startswith("--dir="): workdir = arg.split("=", 1)[1]
            
        os.chdir(workdir)
        print(f"[-] cwd: {os.getcwd()} (can be changed in script)")
    
    @staticmethod
    def getlatestdsp():
        response = operations.fetch(repo + repo_db, True)
        if not response: return False
        db_bytes = io.BytesIO(response.read())
        
        print("[-] getting latest version of steamdeck dsp package...")
        
        xz = tarfile.open(fileobj=db_bytes, mode="r:*")
        latest_ver = [name for name in xz.getnames() if name.startswith(pkgstart) and "debug" not in name and "/" not in name][0]
        print(f"[-] latest version is {latest_ver}")
        
        if not latest_ver:
            print("[X] couldn't get the latest dsp package version")
            sys.exit(1)
        return latest_ver

# fns
class verify:
    @staticmethod
    def file(check, localfile, url=None):
        if not os.path.exists(localfile): return False
        
        if check == "remotesize":
            local_size = int(os.path.getsize(localfile)) # you can never be too safe
            rem_size   = int(uOpen(Request(url, method="HEAD")).headers.get("Content-Length", 0))
            return local_size == rem_size
            
    @staticmethod
    def tree(archive, folder, checkfor="everything"):
        if not (os.path.exists(archive) and os.path.isdir(folder)): return False
        
        expected = subprocess.run(["tar", "-tf", archive], check=True, capture_output=True, text=True).stdout.splitlines()
        if checkfor != "everything": expected = [e for e in expected if any(e.startswith(p) for p in checkfor)]
        missing = [e for e in expected if not os.path.exists(os.path.join(folder, e))]
        return len(missing) == 0

class operations:
    @staticmethod
    def fetch(url, memonly=False): # i am sure theres a way more elegant solution from a pypi package but idfc
        filename = url.split("/")[-1]
        try:
            if not memonly:
                if not verify.file("remotesize", filename, url):
                    print(f"[-] downloading {filename} from {url}")
                    if os.path.exists(filename): os.remove(filename)
                    result = uRet(url, filename)
                    if result: print(f"[-] downloaded {filename}!")
                    return result
                else:
                    print(f"[!] {filename} already exists and is seemingly intact, skipping download")
                    return True
            else:
                print(f"[-] fetching {filename} from {url}")
                result = uOpen(url)
                if result: print(f"[-] fetched {filename}!")
                return result
        except Exception as e:
            print(f"[X] sigh sigh sigh {filename} couldnt be retrieved because {e}")
            sys.exit(1)
            
    @staticmethod
    def extract(filename, extractdir): # boohoo extractdir is local here dont fukigcn care if the name shadows the other extractdir
        if not (verify.tree(filename, extractdir, dsp_pkg_items)):
            print(f"[-] extracting {filename}")
            if os.path.exists(extractdir): shutil.rmtree(extractdir)
            os.makedirs(extractdir)
            subprocess.run(["tar", "-xf", filename, "-C", extractdir, *dsp_pkg_items], check=True)
            print(f"[!] extracted {filename}")
        else: print(f"[!] {extractdir} already exists and is seemingly intact, skipping extraction")

misc.checksys()
misc.getroot()
misc.parseargs()
filename = misc.getlatestdsp() + "-any.pkg.tar.zst"
operations.fetch(repo + filename)
operations.extract(filename, extractdir)
print(f"[-] copying files from dsp package...")
shutil.copytree(f"{extractdir}/usr", "/usr", dirs_exist_ok=True)
print(f"[+] patches complete. restart alsa or your system and enjoy some audio!")
