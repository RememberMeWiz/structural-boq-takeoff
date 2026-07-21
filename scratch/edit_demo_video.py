import os
import sys
import numpy as np
import cv2

INPUT_VIDEO = r"E:\captures\Captures\New Tab - Brave 2026-07-22 02-37-46.mp4"
OUTPUT_VIDEO = r"e:\Users\Louis\Documents\boq_system\outputs\boq_takeoff_demo_edited.mp4"

os.makedirs(os.path.dirname(OUTPUT_VIDEO), exist_ok=True)

def create_title_card(width=1920, height=1080, fps=30, duration_sec=3.5):
    frames = []
    num_frames = int(fps * duration_sec)
    
    for i in range(num_frames):
        # Dark gradient slate background (#0d1117 to #161b22)
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :] = [17, 17, 13]  # BGR #0d1117
        
        # Subtle glowing top/bottom border
        cv2.rectangle(frame, (80, 80), (width - 80, height - 80), (78, 193, 242), 3) # Gold accent #f2c14e
        cv2.rectangle(frame, (90, 90), (width - 90, height - 90), (45, 45, 35), 1)
        
        # Fade in opacity (first 0.8s)
        alpha = min(1.0, (i + 1) / (fps * 0.8))
        
        # Title text
        title = "STRUCTURAL BILL OF QUANTITIES TAKEOFF"
        subtitle = "Automated Material Estimation & Direct Cost Engine"
        badge = "BUILD WEEK HACKATHON 2026 — DEVPOST SUBMISSION"
        
        # Overlay text using Hershey fonts
        cv2.putText(frame, badge, (120, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (120, 220, 150), 2, cv2.LINE_AA)
        cv2.putText(frame, title, (120, 480), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 4, cv2.LINE_AA)
        cv2.putText(frame, title, (120, 480), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (78, 193, 242), 2, cv2.LINE_AA)
        cv2.putText(frame, subtitle, (120, 560), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (200, 200, 200), 2, cv2.LINE_AA)
        
        # Tech tags at bottom
        tags = "Python | OpenCV | Flask | React | Supabase | DPWH CMPD Rates"
        cv2.putText(frame, tags, (120, 920), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 2, cv2.LINE_AA)
        
        if alpha < 1.0:
            frame = (frame * alpha).astype(np.uint8)
            
        frames.append(frame)
    return frames

def create_outro_card(width=1920, height=1080, fps=30, duration_sec=4.0):
    frames = []
    num_frames = int(fps * duration_sec)
    
    for i in range(num_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :] = [17, 17, 13]
        
        cv2.rectangle(frame, (80, 80), (width - 80, height - 80), (78, 193, 242), 3)
        
        title = "THANK YOU FOR REVIEWING!"
        subtitle = "Automating Civil Engineering Quantity Takeoff for Students & Professionals"
        author = "Built by Louis L. Uy  |  Powered by Gemini & Antigravity"
        repo = "GitHub: github.com/RememberMeWiz/structural-boq-takeoff"
        
        cv2.putText(frame, title, (120, 380), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (255, 255, 255), 4, cv2.LINE_AA)
        cv2.putText(frame, title, (120, 380), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (78, 193, 242), 2, cv2.LINE_AA)
        cv2.putText(frame, subtitle, (120, 470), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (220, 220, 220), 2, cv2.LINE_AA)
        cv2.putText(frame, author, (120, 680), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (120, 220, 150), 2, cv2.LINE_AA)
        cv2.putText(frame, repo, (120, 750), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (180, 180, 180), 2, cv2.LINE_AA)
        
        frames.append(frame)
    return frames

def get_caption_for_time(t_sec):
    # Timestamps relative to main video start
    if 2.0 <= t_sec <= 20.0:
        return "1. AUTOMATED DRAWING IMPORT — PDF & DXF Vector Geometry Extraction"
    elif 20.0 <= t_sec <= 45.0:
        return "2. STRUCTURAL FRAMING PLAN CANVAS — Centroid Labels & Interactive Inspector"
    elif 45.0 <= t_sec <= 75.0:
        return "3. COSTED BOQ CHECKLIST — Standard DPWH CMPD Unit Cost Selection Engine"
    elif 75.0 <= t_sec <= 110.0:
        return "4. ONE-CLICK TAKEOFF EXPORT — Executive PDF Reports & Formula BOQ Excel Sheets"
    return None

def process_video():
    print(f"Reading input video: {INPUT_VIDEO}")
    cap = cv2.VideoCapture(INPUT_VIDEO)
    if not cap.isOpened():
        print("Error: Could not open input video.")
        sys.exit(1)
        
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    in_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    in_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    out_w, out_h = 1920, 1080
    print(f"Video Specs: {in_w}x{in_h} @ {fps:.2f} FPS ({total_frames} frames)")
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, fps, (out_w, out_h))
    
    # 1. Write Intro Card
    print("Generating Intro Title Card...")
    intro_frames = create_title_card(out_w, out_h, fps, 3.5)
    for f in intro_frames:
        out.write(f)
        
    # 2. Process Main Video Frames
    print("Processing Main Video Stream with Lower-Third Callouts...")
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_idx += 1
        t_sec = frame_idx / fps
        
        # Resize/letterbox to 1920x1080 if needed
        if in_w != out_w or in_h != out_h:
            canvas = np.zeros((out_h, out_w, 3), dtype=np.uint8)
            # Letterbox scale
            scale = min(out_w / in_w, out_h / in_h)
            nw, nh = int(in_w * scale), int(in_h * scale)
            resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
            off_x = (out_w - nw) // 2
            off_y = (out_h - nh) // 2
            canvas[off_y:off_y+nh, off_x:off_x+nw] = resized
            frame = canvas
            
        # Check lower-third caption banner
        caption = get_caption_for_time(t_sec)
        if caption:
            # Draw sleek dark pill banner at bottom center
            banner_h = 54
            banner_y1 = out_h - 90
            banner_y2 = banner_y1 + banner_h
            
            # Semi-transparent overlay
            sub = frame[banner_y1:banner_y2, 100:out_w-100]
            black_rect = np.full_like(sub, (20, 20, 20))
            blended = cv2.addWeighted(sub, 0.2, black_rect, 0.8, 0)
            frame[banner_y1:banner_y2, 100:out_w-100] = blended
            
            # Banner accent border
            cv2.rectangle(frame, (100, banner_y1), (out_w - 100, banner_y2), (78, 193, 242), 2)
            cv2.putText(frame, caption, (130, banner_y1 + 36), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
            
        out.write(frame)
        if frame_idx % 300 == 0:
            print(f"  Processed {frame_idx}/{total_frames} frames ({frame_idx/total_frames*100:.1f}%)...")
            
    cap.release()
    
    # 3. Write Outro Card
    print("Generating Outro Card...")
    outro_frames = create_outro_card(out_w, out_h, fps, 4.0)
    for f in outro_frames:
        out.write(f)
        
    out.release()
    print(f"\nSUCCESS! Edited demo video saved to: {OUTPUT_VIDEO}")

if __name__ == "__main__":
    process_video()
