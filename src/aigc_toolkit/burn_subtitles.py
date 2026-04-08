"""
Add subtitles to a video with auto line wrap.
"""
import sys
import os
import argparse
import pysrt
import cv2
import numpy as np
import re
from PIL import Image, ImageDraw, ImageFont
import subprocess

def time_to_seconds(t):
    return t.hours * 3600 + t.minutes * 60 + t.seconds + t.milliseconds / 1000.0

def wrap_text(text, font, max_width):
    # Remove existing newlines
    text = text.replace('\n', ' ').strip()
    
    # Split by common Chinese/English punctuation keeping the punctuation attached
    segments = re.split(r'([，。！？,\.\!\?]+)', text)
    parts = []
    for i in range(0, len(segments) - 1, 2):
        parts.append(segments[i] + segments[i+1])
    if len(segments) % 2 == 1 and segments[-1]:
        parts.append(segments[-1])
        
    lines = []
    current_line = ""
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        test_line = current_line + part if current_line else part
        bbox = font.getbbox(test_line)
        w = bbox[2] - bbox[0]
        
        if w <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
                current_line = ""
                
            # Test if part itself fits on a new line
            b = font.getbbox(part)
            if (b[2] - b[0]) <= max_width:
                current_line = part
            else:
                # Part is still wider than max_width, hard wrap character by character
                temp_line = ""
                for char in part:
                    test_char_line = temp_line + char
                    cb = font.getbbox(test_char_line)
                    cw = cb[2] - cb[0]
                    if cw <= max_width:
                        temp_line = test_char_line
                    else:
                        if temp_line:
                            lines.append(temp_line)
                        temp_line = char
                current_line = temp_line
            
    if current_line:
        lines.append(current_line)
        
    return lines

def main():
    parser = argparse.ArgumentParser(description="Burn subtitles into a video.")
    parser.add_argument("--video_path", help="Path to the input video file")
    parser.add_argument("--srt_path", help="Path to the subtitle file (.srt)")
    parser.add_argument("--out_path", help="Path to the output video file")
    parser.add_argument("--font_path", default="/System/Library/Fonts/STHeiti Light.ttc", help="Path to the font file")
    args = parser.parse_args()
    
    video_path = args.video_path
    srt_path = args.srt_path
    out_path = args.out_path
    font_path = args.font_path
    
    subs = pysrt.open(srt_path)
    
    intervals = []
    for sub in subs:
        intervals.append((time_to_seconds(sub.start), time_to_seconds(sub.end), sub.text))
    
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    font_size = int(height * 0.04)
    if font_size < 12: font_size = 12
    font = ImageFont.truetype(font_path, font_size, index=0)
    
    temp_video = out_path + ".tmp.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))
    
    max_text_width = int(width * 0.9)  # 90% of screen width
    
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        t = frame_idx / fps
        text = None
        for start, end, txt in intervals:
            if start <= t <= end:
                text = txt
                break
                
        if text:
            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)
            
            lines = wrap_text(text, font, max_text_width)
            
            # Calculate total height of the text block
            line_height = font_size * 1.2
            total_text_height = len(lines) * line_height
            
            # Position at bottom with a margin
            bottom_margin = font_size * 0.5
            y_pos = height - total_text_height - bottom_margin
            
            for line in lines:
                bbox = font.getbbox(line)
                w = bbox[2] - bbox[0]
                x = (width - w) / 2
                
                stroke_color = "black"
                stroke_width = max(1, int(font_size * 0.05))
                draw.text((x, y_pos), line, font=font, fill="white", stroke_width=stroke_width, stroke_fill=stroke_color)
                y_pos += line_height
                
            frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            
        out.write(frame)
        frame_idx += 1
        if frame_idx % 100 == 0:
            print(f"Processed {frame_idx}/{total_frames} frames...")
            
    cap.release()
    out.release()
    print("Video processed. Merging audio...")
    
    subprocess.run(["ffmpeg", "-y", "-i", temp_video, "-i", video_path, "-c:v", "libx264", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0", "-shortest", out_path], check=True)
    os.remove(temp_video)
    print(f"Final video saved to {out_path}")

if __name__ == "__main__":
    main()