import cv2
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import qrcode
import os, time, threading, sys
from datetime import datetime
import cloudinary
import cloudinary.uploader
import winsound

# ================= EXE SAFE =================
def resource_path(p):
    try:
        base = sys._MEIPASS
    except:
        base = os.path.abspath(".")
    return os.path.join(base, p)

# ================= Cloudinary =================
cloudinary.config(
    cloud_name="*******",
    api_key="**********",
    api_secret="j*******"
)

# ================= SETTINGS =================
EVENT_NAME = "HAPPY 3id"
MODE = "group"  # group | portrait
ROTATIONS = [0, 90, 180, 270]
rotation_index = 0

# ================= Camera =================
camera_index = 0  # 0 laptop | 1 capture card

def open_camera(idx):
    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
    return cap

cap = open_camera(camera_index)

# ================= Frames =================
frame_land = Image.open(resource_path("frame_landscape.png")).convert("RGBA")
frame_port = Image.open(resource_path("frame_portrait.png")).convert("RGBA")

# ================= State =================
last_frame = None
photo_count = 0
showing_qr = False
countdown_val = 0

# ================= Sounds =================
def play_shutter():
    winsound.PlaySound(resource_path("camera.wav"),
                       winsound.SND_FILENAME | winsound.SND_ASYNC)

def play_beep():
    winsound.PlaySound(resource_path("beep.wav"),
                       winsound.SND_FILENAME | winsound.SND_ASYNC)

# ================= Crop Nikon HUD =================
def crop_overlays(frame):
    h, w = frame.shape[:2]
    return frame[
        int(h*0.08):int(h*0.88),
        int(w*0.10):int(w*0.90)
    ]

# ================= Helpers =================
def landscape_to_portrait(frame):
    h, w = frame.shape[:2]
    crop_w = int(h * 9 / 16)
    x1 = (w - crop_w) // 2
    return frame[:, x1:x1 + crop_w]

def apply_rotation(frame):
    r = ROTATIONS[rotation_index]
    if r == 90:
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    if r == 180:
        return cv2.rotate(frame, cv2.ROTATE_180)
    if r == 270:
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return frame

def resize_canvas(img, tw, th):
    return img.resize((tw, th), Image.LANCZOS)

# ================= Countdown =================
def start_countdown():
    global countdown_val
    if showing_qr:
        return
    countdown_val = 3
    run_countdown()

def run_countdown():
    global countdown_val
    if countdown_val > 0:
        countdown_label.config(text=str(countdown_val))
        play_beep()
        countdown_val -= 1
        root.after(1000, run_countdown)
    else:
        countdown_label.config(text="")
        capture()

# ================= Buttons =================
def toggle_mode():
    global MODE
    MODE = "portrait" if MODE == "group" else "group"
    mode_btn.config(text="👤 فردي" if MODE=="portrait" else "👥 جماعي")

def toggle_rotation():
    global rotation_index
    rotation_index = (rotation_index + 1) % len(ROTATIONS)
    rot_btn.config(text=f"🔄 {ROTATIONS[rotation_index]}°")

def toggle_camera():
    global cap, camera_index
    camera_index = 1 if camera_index == 0 else 0
    cap.release()
    cap = open_camera(camera_index)
    cam_btn.config(text="📷 كاميرا برو" if camera_index else "💻 كاميرا لابتوب")

# ================= Capture =================
def capture():
    global photo_count, showing_qr
    if last_frame is None or showing_qr:
        return

    showing_qr = True
    play_shutter()

    frame = crop_overlays(last_frame.copy())

    if MODE == "portrait":
        frame = landscape_to_portrait(frame)
        tw, th = 1080, 1920
        overlay = frame_port
    else:
        tw, th = 1920, 1080
        overlay = frame_land

    frame = apply_rotation(frame)
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    img = resize_canvas(img, tw, th)
    overlay = overlay.resize(img.size)

    final = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(final)
    draw.text((40, final.height-80), EVENT_NAME, fill="white")
    draw.text((40, final.height-40),
              datetime.now().strftime("%d-%m-%Y"), fill="white")

    os.makedirs("images", exist_ok=True)
    final.save(f"images/photo_{int(time.time())}.png", compress_level=0)

    photo_count += 1
    counter.config(text=f"📸 {photo_count}")

    threading.Thread(target=upload_and_show_qr,
                     args=(final,), daemon=True).start()

# ================= Upload + QR =================
def upload_and_show_qr(final_img):
    global showing_qr
    temp = "temp.jpg"
    final_img.convert("RGB").save(temp, quality=90)
    res = cloudinary.uploader.upload(temp, folder="party_photos")
    os.remove(temp)

    qr = qrcode.make(res["secure_url"]).resize((420,420))
    qr_img = ImageTk.PhotoImage(qr)

    def show():
        cam.pack_forget()
        ctrl.place_forget()
        qr_lbl.config(image=qr_img)
        qr_lbl.image = qr_img
        qr_lbl.pack(expand=True)
        back_btn.pack(pady=10)

    root.after(0, show)

# ================= Back / Retry =================
def back_to_camera():
    global showing_qr
    qr_lbl.pack_forget()
    back_btn.pack_forget()
    cam.pack(pady=10)
    ctrl.place(relx=0, rely=0.82, relwidth=1)
    countdown_label.config(text="")
    showing_qr = False

def retry_capture():
    back_to_camera()

# ================= Live =================
def update():
    global last_frame
    if not showing_qr:
        ret, frame = cap.read()
        if ret:
            frame = crop_overlays(frame)
            last_frame = frame.copy()

            preview = frame
            if MODE == "portrait":
                preview = landscape_to_portrait(frame)

            preview = apply_rotation(preview)
            preview = cv2.resize(preview,
                (620,1100) if MODE=="portrait" else (1100,620))

            img = ImageTk.PhotoImage(
                Image.fromarray(cv2.cvtColor(preview, cv2.COLOR_BGR2RGB))
            )
            cam.config(image=img)
            cam.imgtk = img

    cam.after(15, update)

# ================= GUI =================
root = tk.Tk()
root.geometry("1400x900")
root.title("Photo Booth Pro")

cam = tk.Label(root)
cam.pack(pady=10)

countdown_label = tk.Label(root, font=("Arial",90),
                           fg="red", bg="black")
countdown_label.place(relx=0.5, rely=0.35, anchor="center")

qr_lbl = tk.Label(root)

back_btn = tk.Button(root, text="⬅ رجوع",
                     font=("Arial",20),
                     bg="black", fg="white",
                     command=back_to_camera)

ctrl = tk.Frame(root, bg="black", height=90)
ctrl.place(relx=0, rely=0.82, relwidth=1)

tk.Button(ctrl, text="📸 تصوير", font=("Arial",20),
          bg="green", fg="white",
          command=start_countdown).pack(side="left", padx=10)

tk.Button(ctrl, text="🔄 إعادة تصوير",
          font=("Arial",18),
          bg="#444444", fg="white",
          command=retry_capture).pack(side="left", padx=10)

mode_btn = tk.Button(ctrl, text="👥 جماعي",
                     font=("Arial",16),
                     command=toggle_mode)
mode_btn.pack(side="left", padx=10)

rot_btn = tk.Button(ctrl, text="🔄 0°",
                    font=("Arial",16),
                    command=toggle_rotation)
rot_btn.pack(side="left", padx=10)

cam_btn = tk.Button(ctrl, text="💻 كاميرا لابتوب",
                    font=("Arial",16),
                    command=toggle_camera)
cam_btn.pack(side="left", padx=10)

counter = tk.Label(ctrl, text="📸 0",
                   fg="white", bg="black",
                   font=("Arial",14))
counter.pack(side="right", padx=20)

# ================= Start =================
update()
root.mainloop()
