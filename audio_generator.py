
import os
import tempfile
from pydub import AudioSegment
from pydub.generators import Sine
import random
import time
import azure.cognitiveservices.speech as speechsdk

class AudioGenerator:
    def __init__(self, azure_speech_key=None, azure_region=None):
        """Initialize the audio generator with Azure Speech Services"""
        self.temp_dir = tempfile.mkdtemp()
        self.azure_speech_key = azure_speech_key
        self.azure_region = azure_region
        
        if self.azure_speech_key and self.azure_region:
            self.speech_config = speechsdk.SpeechConfig(
                subscription=self.azure_speech_key, 
                region=self.azure_region
            )
            # Use a natural English voice
            self.speech_config.speech_synthesis_voice_name = "en-US-AriaNeural"
        else:
            self.speech_config = None
        
    def set_azure_credentials(self, speech_key, region):
        """Set Azure Speech Services credentials"""
        self.azure_speech_key = speech_key
        self.azure_region = region
        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.azure_speech_key, 
            region=self.azure_region
        )
        self.speech_config.speech_synthesis_voice_name = "en-US-AriaNeural"
        
    def generate_conversation_audio(self, conversation, add_background=False, background_type=None):
        """
        Generate audio files from conversation script using Azure Speech Services
        
        Args:
            conversation (list): List of conversation lines with speaker and text
            add_background (bool): Whether to add background audio
            background_type (str): Type of background audio to add
            
        Returns:
            dict: Dictionary containing paths to generated audio files
        """
        if not self.speech_config:
            raise ValueError("Azure Speech Services credentials are required")
            
        try:
            individual_files = {}
            combined_segments = []
            
            # Define different voices for different speakers
            voices = [
                "en-US-AriaNeural",      # Female voice
                "en-US-DavisNeural",     # Male voice
                "en-US-JennyNeural",     # Female voice
                "en-US-GuyNeural"        # Male voice
            ]
            
            speaker_voices = {}
            voice_index = 0
            
            # Generate individual audio files for each speaker line
            for i, line in enumerate(conversation):
                speaker = line.get('speaker', f'Speaker{i}')
                text = line.get('text', '')
                
                if not text.strip():
                    continue
                
                # Assign voice to speaker if not already assigned
                if speaker not in speaker_voices:
                    speaker_voices[speaker] = voices[voice_index % len(voices)]
                    voice_index += 1
                
                # Configure voice for this speaker
                self.speech_config.speech_synthesis_voice_name = speaker_voices[speaker]
                
                # Create synthesizer - temporarily use WAV for Azure, then convert to MP3
                temp_wav_file = os.path.join(self.temp_dir, f"{speaker}_{i}_temp.wav")
                audio_config = speechsdk.audio.AudioOutputConfig(filename=temp_wav_file)
                synthesizer = speechsdk.SpeechSynthesizer(
                    speech_config=self.speech_config, 
                    audio_config=audio_config
                )
                
                # Synthesize speech
                result = synthesizer.speak_text_async(text).get()
                
                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    # Load the generated audio file and convert to MP3
                    audio_segment = AudioSegment.from_wav(temp_wav_file)
                    
                    # Export individual file as MP3
                    mp3_file = os.path.join(self.temp_dir, f"{speaker}_{i}.mp3")
                    audio_segment.export(mp3_file, format="mp3")
                    
                    # Add pause between speakers (1 second)
                    if combined_segments:
                        combined_segments.append(AudioSegment.silent(duration=1000))
                    
                    combined_segments.append(audio_segment)
                    
                    # Store individual MP3 file path
                    individual_files[f"{speaker}_{i}"] = mp3_file
                    
                    # Clean up temporary WAV file
                    if os.path.exists(temp_wav_file):
                        os.remove(temp_wav_file)
                    
                elif result.reason == speechsdk.ResultReason.Canceled:
                    cancellation_details = result.cancellation_details
                    raise Exception(f"Speech synthesis canceled: {cancellation_details.reason}")
                else:
                    raise Exception(f"Speech synthesis failed: {result.reason}")
                
                # Small delay to avoid overwhelming the service
                time.sleep(0.1)
            
            if not combined_segments:
                raise ValueError("No valid audio segments generated")
            
            # Combine all segments
            combined_audio = AudioSegment.empty()
            for segment in combined_segments:
                combined_audio += segment
            
            # Add background audio if requested
            if add_background and background_type and background_type != "none":
                background_audio = self._generate_background_audio(
                    len(combined_audio), background_type
                )
                # Mix background at lower volume (reduce by 15dB)
                combined_audio = combined_audio.overlay(background_audio - 15)
            
            # Export combined audio as MP3
            combined_file = os.path.join(self.temp_dir, "combined_conversation.mp3")
            combined_audio.export(combined_file, format="mp3")
            
            return {
                "combined": combined_file,
                "individual": individual_files
            }
            
        except Exception as e:
            raise Exception(f"Failed to generate audio with Azure Speech Services: {e}")
    
    def _generate_background_audio(self, duration_ms, background_type):
        """
        Load and process background audio from local files (MP3 and WAV support)
        
        Args:
            duration_ms (int): Duration in milliseconds
            background_type (str): Type of background audio
            
        Returns:
            AudioSegment: Processed background audio
        """
        try:
            # Path to background audio files
            background_audio_dir = "background_audio"
            
            # Check for MP3 file first, then WAV
            mp3_file = os.path.join(background_audio_dir, f"{background_type}.mp3")
            wav_file = os.path.join(background_audio_dir, f"{background_type}.wav")
            
            background_audio = None
            
            # Try to load MP3 file first
            if os.path.exists(mp3_file):
                try:
                    background_audio = AudioSegment.from_mp3(mp3_file)
                except Exception as e:
                    print(f"Error loading MP3 file {mp3_file}: {e}")
            
            # If MP3 didn't work, try WAV
            if background_audio is None and os.path.exists(wav_file):
                try:
                    background_audio = AudioSegment.from_wav(wav_file)
                except Exception as e:
                    print(f"Error loading WAV file {wav_file}: {e}")
            
            if background_audio is not None:
                # Adjust the duration to match the conversation
                if len(background_audio) < duration_ms:
                    # Loop the background audio if it's shorter than needed
                    loops_needed = (duration_ms // len(background_audio)) + 1
                    background_audio = background_audio * loops_needed
                
                # Trim to exact duration
                background_audio = background_audio[:duration_ms]
                
                # Reduce volume for background effect
                background_audio = background_audio - 15  # Reduce by 15dB
                
                return background_audio
            
            else:
                # If no files exist, fallback to generated ambient noise
                print(f"Warning: Background audio file not found: {mp3_file} or {wav_file}")
                print("Falling back to generated ambient noise")
                return self._generate_ambient_noise(duration_ms, volume=-25)
                
        except Exception as e:
            print(f"Error loading background audio: {e}")
            # If background generation fails, return silence
            return AudioSegment.silent(duration=duration_ms)
    
    def _generate_ambient_noise(self, duration_ms, volume=-30):
        """
        Generate ambient noise using multiple frequency layers
        
        Args:
            duration_ms (int): Duration in milliseconds
            volume (int): Volume in dB
            
        Returns:
            AudioSegment: Ambient noise audio segment
        """
        # Start with silence
        noise = AudioSegment.silent(duration=duration_ms)
        
        # Add low frequency rumble
        low_freq = Sine(60).to_audio_segment(duration=duration_ms)
        low_freq = low_freq + volume - 15
        noise = noise.overlay(low_freq)
        
        # Add mid frequency ambient
        for freq in [150, 300, 450, 600]:
            sine_wave = Sine(freq).to_audio_segment(duration=duration_ms)
            sine_wave = sine_wave + volume - 10
            noise = noise.overlay(sine_wave)
        
        # Add high frequency subtle hiss
        for freq in [1000, 1500, 2000]:
            sine_wave = Sine(freq).to_audio_segment(duration=duration_ms)
            sine_wave = sine_wave + volume - 20
            noise = noise.overlay(sine_wave)
        
        return noise
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            import shutil
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass
    
    def manual_cleanup(self):
        """Manually clean up temporary files when explicitly called"""
        self.cleanup()
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        # Don't automatically cleanup on deletion to prevent file access issues
        pass
