"""
Unified TTS generation on MLX.
"""
import sys
import os
import shutil
import re
import subprocess
import tempfile
import argparse
import time
from pathlib import Path
import mlx.core as mx

from mlx_audio.tts.utils import load_model
from mlx_audio.tts.generate import generate_audio


def split_sentences(text):
    sentences = re.split(r'([。？！!])', text)
    raw_chunks = []
    for i in range(0, len(sentences)-1, 2):
        chunk = sentences[i] + sentences[i+1]
        if chunk.strip():
            raw_chunks.append(chunk.strip())
    if len(sentences) % 2 != 0 and sentences[-1].strip():
        raw_chunks.append(sentences[-1].strip())
        
    chunks = []
    current_chunk = ""
    for rc in raw_chunks:
        current_chunk += rc
        if len(current_chunk) >= 30:
            chunks.append(current_chunk)
            current_chunk = ""
            
    if current_chunk:
        if chunks:
            chunks[-1] += current_chunk
        else:
            chunks.append(current_chunk)
            
    return chunks


def cleanup_subtitle(text):
    text = re.sub(r'\[.*?\]', '', text)
    return text
    

def ms_to_srt_time(ms):
    s = ms / 1000.0
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = int(s % 60)
    msec = int((s * 1000) % 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{msec:03d}"

def main():
    parser = argparse.ArgumentParser(description="Unified TTS generation on MLX")
    parser.add_argument("--text", required=True, help="Text to generate audio for")
    parser.add_argument("--output", required=True, help="Path to save the output WAV file")
    parser.add_argument("--ref_audio", default=None, help="Path to reference audio file")
    parser.add_argument("--ref_text", default="", help="Reference text for the voice clone")
    parser.add_argument("--srt", help="Optional path to save output SRT subtitles")
    parser.add_argument("--model", default=None, help="Model path/alias")
    parser.add_argument("--model_type", choices=["qwen3", "fishaudio"], default="fishaudio", help="Model type (qwen3 or fishaudio).")
    parser.add_argument("--speed_factor", type=float, default=1.0, help="Speed factor for audio generation (default: 1.0)")
    
    args = parser.parse_args()
    
    text = args.text
    final_output_file = os.path.abspath(args.output)
    ref_audio_path = os.path.abspath(args.ref_audio) if args.ref_audio else None
    ref_text = args.ref_text
    srt_output_file = os.path.abspath(args.srt) if args.srt else None
    speed_factor = args.speed_factor
    
    # Infer model type and default model if not provided
    model_path = args.model
    model_type = args.model_type
            
    if not model_path:
        if model_type == "fishaudio":
            model_path = "mlx-community/fish-audio-s2-pro-8bit"
        else:
            model_path = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16"
            
    print(f"Model Type: {model_type}")
    print(f"Model Path: {model_path}")
    
    print("Loading model...")
    model = load_model(model_path, strict=False)

    print(f"Generating: {text}")

    splits = text.split('\n')
    chunks = []
    for s in splits:
        if len(s) > 200:
            # split long text just to be safe
            chunks.extend(split_sentences(s))
        else:
            chunks.append(s)
    print(f"Split into {len(chunks)} chunks.")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        chunk_files = []
        chunk_durations = []
        for i, chunk in enumerate(chunks):
            print(f"Generating chunk {i}: {chunk}")            
            generate_audio(model=model, text=chunk, ref_audio=ref_audio_path, ref_text=ref_text, output_path=temp_dir)
            
            files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.endswith(".wav") and not f.startswith("chunk_")]
            if not files:
                continue
            latest_file = max(files, key=os.path.getctime)
            
            new_name = os.path.join(temp_dir, f"chunk_{i:03d}.wav")
            shutil.move(latest_file, new_name)
            chunk_files.append(new_name)
            
            # Get duration of generated chunk
            dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", chunk_files[-1]]
            dur_str = subprocess.check_output(dur_cmd).decode("utf-8").strip()
            duration_ms = float(dur_str) * 1000
            chunk_durations.append(duration_ms)
            
        if not chunk_files:
            print("No audio generated.")
            sys.exit(1)
            
        print("Concatenating chunks...")
        concat_list = os.path.join(temp_dir, "concat.txt")
        with open(concat_list, "w") as f:
            for cf in chunk_files:
                f.write(f"file '{cf}'\n")
                
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-filter:a", f"atempo={speed_factor}", final_output_file], check=True)
        print(f"Saved final to {final_output_file}")
    
    if srt_output_file:
        with open(srt_output_file, "w", encoding="utf-8") as f:
            current_ms = 0.0
            sub_idx = 1
            for i, (chunk_text, dur) in enumerate(zip(chunks, chunk_durations)):
                chunk_text = cleanup_subtitle(chunk_text)
                adjusted_dur = dur / speed_factor
                
                parts = re.split(r'([，、：；,;])', chunk_text)
                merged_parts = []
                for j in range(0, len(parts)-1, 2):
                    merged_parts.append(parts[j] + parts[j+1])
                if len(parts) % 2 != 0 and parts[-1]:
                    merged_parts.append(parts[-1])
                    
                sub_chunks = []
                curr_sub = ""
                for mp in merged_parts:
                    if len(curr_sub) + len(mp) <= 20:
                        curr_sub += mp
                    else:
                        if curr_sub:
                            sub_chunks.append(curr_sub)
                            curr_sub = ""
                        while len(mp) > 20:
                            sub_chunks.append(mp[:20])
                            mp = mp[20:]
                        curr_sub = mp
                if curr_sub:
                    sub_chunks.append(curr_sub)
                
                total_chars = sum(len(sc) for sc in sub_chunks)
                
                for sc in sub_chunks:
                    sc_len = len(sc)
                    sc_dur = adjusted_dur * (sc_len / total_chars) if total_chars > 0 else 0
                    
                    start_str = ms_to_srt_time(current_ms)
                    end_str = ms_to_srt_time(current_ms + sc_dur)
                    
                    f.write(f"{sub_idx}\n")
                    f.write(f"{start_str} --> {end_str}\n")
                    f.write(f"{sc.strip()}\n\n")
                    
                    current_ms += sc_dur
                    sub_idx += 1
                    
        print(f"Saved SRT to {srt_output_file}")

if __name__ == "__main__":
    main()
