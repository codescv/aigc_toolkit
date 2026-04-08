"""
Speech-to-Text (STT) generation using mlx-whisper.
"""
import argparse
import sys
import os
import mlx_whisper

def ms_to_srt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    sec = int(seconds % 60)
    msec = int((seconds * 1000) % 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{msec:03d}"

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio to text or SRT subtitles using mlx-whisper.")
    parser.add_argument("--audio", required=True, help="Path to the input audio file.")
    parser.add_argument("--output", help="Path to save the output text or SRT file.")
    parser.add_argument("--model", default="mlx-community/whisper-large-v3-turbo", help="The Hugging Face model ID or local path to use.")
    parser.add_argument("--srt", action="store_true", help="Force output as SRT format. Automatically inferred if output file ends with .srt.")
    
    args = parser.parse_args()

    audio_path = os.path.abspath(args.audio)
    if not os.path.exists(audio_path):
        print(f"Error: Input audio file not found at {audio_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Recognizing: {audio_path}")
    print(f"Loading model {args.model}...")

    try:
        result = mlx_whisper.transcribe(
            audio_path,
            path_or_hf_repo=args.model
        )
    except Exception as e:
        print(f"Failed to transcribe audio: {e}", file=sys.stderr)
        sys.exit(1)

    is_srt = args.srt or (args.output and args.output.lower().endswith(".srt"))

    if is_srt:
        content = ""
        for i, segment in enumerate(result.get("segments", []), start=1):
            start_str = ms_to_srt_time(segment["start"])
            end_str = ms_to_srt_time(segment["end"])
            text = segment["text"].strip()
            content += f"{i}\n{start_str} --> {end_str}\n{text}\n\n"
    else:
        content = result.get("text", "").strip()

    if args.output:
        output_path = os.path.abspath(args.output)
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Saved output to {output_path}")
        except Exception as e:
            print(f"Failed to save output to {output_path}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("--- Result ---")
        print(content)

if __name__ == "__main__":
    main()