"""
DroidCam Connection Diagnostic
Run this script and type your phone's IP when asked.
It will test every possible URL and tell you exactly which one works.
"""
import cv2
import sys

def test_url(url, timeout=4):
    print(f"  Testing: {url} ...", end=" ", flush=True)
    cap = cv2.VideoCapture(url)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout * 1000)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout * 1000)
    if not cap.isOpened():
        print("FAILED (could not open)")
        cap.release()
        return False
    ret, frame = cap.read()
    cap.release()
    if ret and frame is not None:
        h, w = frame.shape[:2]
        print(f"OK  ({w}x{h})")
        return True
    else:
        print("FAILED (opened but no frame)")
        return False

ip = input("\nEnter your phone IP (shown in DroidCam app): ").strip()
if not ip:
    print("No IP entered. Exiting.")
    sys.exit(1)

ips_to_try = [ip, "127.0.0.1", "localhost"]
ports       = ["4747", "4748", "8080"]
paths       = ["/video", "/videofeed", "/mjpeg", "/shot.jpg"]

print(f"\nScanning all DroidCam URL combinations for {ip}...\n")
working = []
for h in ips_to_try:
    for p in ports:
        for path in paths:
            url = f"http://{h}:{p}{path}"
            if test_url(url):
                working.append(url)

print("\n" + "="*50)
if working:
    print(f"\nWORKING URLs found:")
    for u in working:
        print(f"   {u}")
    print(f"\nUse this URL in Gesture Mouse IP box: {working[0]}")
else:
    print("\nNo working stream found.")
    print("\nPossible reasons:")
    print("  1. Phone and PC are NOT on the same Wi-Fi network")
    print("  2. DroidCam app is not open/streaming on the phone")
    print("  3. Windows Firewall is blocking port 4747")
    print("  4. If using USB: enable USB tethering on your phone")

input("\nPress Enter to exit...")
