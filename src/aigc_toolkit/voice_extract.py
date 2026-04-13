"""
Voice extraction and enhancement using MLX models.
Uses Demucs for separation and DeepFilterNet for enhancement.
"""
import os
import argparse
import tempfile
from pathlib import Path
import soundfile as sf
from demucs_mlx import Separator
from mlx_audio.sts.models.deepfilternet import DeepFilterNetModel

def separate_voice(input_path: str, output_path: str) -> str:
    """
    Separate voice from background using Demucs.
    
    Args:
        input_path: Path to the input audio file.
        output_path: Path to save the separated vocals file.
        
    Returns:
        Path to the separated vocals file.
    """
    print(f"Separating voice from {input_path} using Demucs-MLX...")
    separator = Separator()
    
    # separate_audio_file returns (stems_tensor, stems_dict)
    stems, stems_dict = separator.separate_audio_file(input_path)
    
    # Infer how to handle the output based on type
    if isinstance(stems_dict, dict):
        vocals_data = stems_dict.get('vocals')
        if vocals_data is not None:
            sr = separator.samplerate if hasattr(separator, 'samplerate') else 44100
            # Check if we need to transpose (channels, length) -> (length, channels)
            if len(vocals_data.shape) == 2 and vocals_data.shape[0] <= 2:
                vocals_data = vocals_data.T
            sf.write(output_path, vocals_data, sr)
            print(f"Saved separated vocals to {output_path}")
            return output_path
    
    print(f"Warning: Could not extract vocals automatically. Result type: {type(stems)}")
    print(f"Stems dict type: {type(stems_dict)}")
    raise RuntimeError("Failed to extract vocals. Check logs for output structure.")

def enhance_speech(input_path: str, output_path: str):
    """
    Enhance speech quality using DeepFilterNet.
    
    Args:
        input_path: Path to the input audio file (e.g., separated vocals).
        output_path: Path to save the enhanced audio file.
    """
    print(f"Enhancing speech from {input_path} using DeepFilterNet-MLX...")
    
    import librosa
    
    print("Resampling to 48000 Hz...")
    audio, sr = librosa.load(input_path, sr=48000)
    
    # Save to a temp file at 48000 Hz
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        resampled_path = temp_file.name
        
    sf.write(resampled_path, audio, 48000)
    
    try:
        # Load the pretrained model
        model = DeepFilterNetModel.from_pretrained()
        
        # Enhance the file
        model.enhance_file(str(resampled_path), str(output_path))
        print(f"Enhanced audio saved to {output_path}")
    finally:
        # Clean up temp file
        if os.path.exists(resampled_path):
            os.unlink(resampled_path)

def main():
    """
    Main entry point for the voice extraction script.
    """
    parser = argparse.ArgumentParser(description="Voice Extract and Enhance using MLX")
    parser.add_argument("--input", required=True, help="Path to input audio file")
    parser.add_argument("--output", required=True, help="Path to save the output audio file")
    parser.add_argument("--separate_only", action="store_true", help="Only run separation (Demucs)")
    parser.add_argument("--enhance_only", action="store_true", help="Only run enhancement (DeepFilterNet)")
    
    args = parser.parse_args()
    
    # Expand user path (~)
    input_path = os.path.abspath(os.path.expanduser(args.input))
    output_path = os.path.abspath(os.path.expanduser(args.output))
    
    if not os.path.exists(input_path):
        print(f"Error: Input file {input_path} does not exist.")
        return
        
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Use a temp file for voice.wav as requested by user
        temp_vocals_path = os.path.join(temp_dir, "voice.wav")
        
        current_audio = input_path
        
        if not args.enhance_only:
            # Run separation
            try:
                current_audio = separate_voice(input_path, temp_vocals_path)
            except Exception as e:
                print(f"Separation failed: {e}")
                return
            
        if not args.separate_only:
            # Run enhancement
            try:
                enhance_speech(current_audio, output_path)
            except Exception as e:
                print(f"Enhancement failed: {e}")
                return
        else:
            # If separate_only, we just copy the temp result to the final output
            import shutil
            shutil.copy(current_audio, output_path)
            print(f"Copied separated audio to {output_path}")
            
    print(f"Done. Processed audio saved to {output_path}")

if __name__ == "__main__":
    main()
