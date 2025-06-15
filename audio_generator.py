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
            # Use natural English voices
            self.speech_config.speech_synthesis_voice_name = "en-US-AriaNeural"
        else:
            self.speech_config = None
        
    def generate_conversation_audio(self, conversation, add_background=False, background_type=None, uploaded_background=None):
        """
        Generate audio files from conversation script using Azure Speech Services
        
        Args:
            conversation (list): List of conversation lines with speaker and text
            add_background (bool): Whether to add background audio
            background_type (str): Type of background audio to add
            uploaded_background: Streamlit uploaded file object for custom background audio
            
        Returns:
            dict: Dictionary containing paths to generated audio files
        """
        try:
            individual_files = {}
            combined_segments = []
            
            # Check if Azure Speech Services is configured
            if not self.speech_config:
                raise ValueError("Azure Speech Services not configured. Please set your Azure credentials.")
            
            # Generate individual audio files for each speaker line using Azure Speech
            for i, line in enumerate(conversation):
                speaker = line.get('speaker', f'Speaker{i}')
                text = line.get('text', '')
                
                if not text.strip():
                    continue
                
                # Create a temporary WAV file for Azure Speech output
                temp_wav_file = os.path.join(self.temp_dir, f"{speaker}_{i}_temp.wav")
                
                # Configure Azure Speech synthesis
                audio_config = speechsdk.audio.AudioOutputConfig(filename=temp_wav_file)
                synthesizer = speechsdk.SpeechSynthesizer(
                    speech_config=self.speech_config, 
                    audio_config=audio_config
                )
                
                # Synthesize speech
                result = synthesizer.speak_text_async(text).get()
                
                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    # Load the generated audio file
                    audio_segment = AudioSegment.from_wav(temp_wav_file)
                    
                    # Add pause between speakers (1 second)
                    if combined_segments:
                        combined_segments.append(AudioSegment.silent(duration=1000))
                    
                    combined_segments.append(audio_segment)
                    
                    # Store individual file path
                    individual_wav = os.path.join(self.temp_dir, f"{speaker}_{i}.wav")
                    audio_segment.export(individual_wav, format="wav")
                    individual_files[f"{speaker}_{i}"] = individual_wav
                    
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
            if add_background:
                if uploaded_background:
                    print(f"Adding uploaded background audio")
                    background_audio = self._load_uploaded_background(
                        uploaded_background, len(combined_audio)
                    )
                    if background_audio:
                        # Mix background at lower volume (-20dB)
                        combined_audio = combined_audio.overlay(background_audio - 20)
                        print(f"Uploaded background audio added successfully")
                elif background_type and background_type != "none":
                    print(f"Adding generated background audio: {background_type}")
                    background_audio = self._generate_background_audio(
                        len(combined_audio), background_type
                    )
                    # Mix background at lower volume (-20dB)
                    combined_audio = combined_audio.overlay(background_audio - 20)
                    print(f"Generated background audio added successfully")
            
            # Export combined audio
            combined_file = os.path.join(self.temp_dir, "combined_conversation.wav")
            combined_audio.export(combined_file, format="wav")
            
            return {
                "combined": combined_file,
                "individual": individual_files
            }
            
        except Exception as e:
            raise Exception(f"Failed to generate audio: {e}")
    
    def _load_uploaded_background(self, uploaded_file, target_duration_ms):
        """
        Load and process uploaded background audio file
        
        Args:
            uploaded_file: Streamlit uploaded file object
            target_duration_ms (int): Target duration in milliseconds
            
        Returns:
            AudioSegment: Processed background audio
        """
        try:
            # Save uploaded file to temporary location
            temp_bg_file = os.path.join(self.temp_dir, f"uploaded_bg_{uploaded_file.name}")
            with open(temp_bg_file, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Load audio file
            if uploaded_file.name.lower().endswith('.mp3'):
                background_audio = AudioSegment.from_mp3(temp_bg_file)
            elif uploaded_file.name.lower().endswith('.wav'):
                background_audio = AudioSegment.from_wav(temp_bg_file)
            else:
                raise ValueError("Unsupported audio format")
            
            # Adjust duration to match conversation
            bg_duration = len(background_audio)
            if bg_duration < target_duration_ms:
                # Loop the background audio if it's shorter than conversation
                loops_needed = (target_duration_ms // bg_duration) + 1
                background_audio = background_audio * loops_needed
            
            # Trim to exact duration
            background_audio = background_audio[:target_duration_ms]
            
            # Clean up temporary file
            os.remove(temp_bg_file)
            
            return background_audio
            
        except Exception as e:
            print(f"Error loading uploaded background audio: {e}")
            return None
    
    def _generate_background_audio(self, duration_ms, background_type):
        """
        Generate simple background audio based on type
        
        Args:
            duration_ms (int): Duration in milliseconds
            background_type (str): Type of background audio
            
        Returns:
            AudioSegment: Generated background audio
        """
        try:
            print(f"Generating {background_type} background audio for {duration_ms}ms")
            
            if background_type == "classroom":
                # Generate soft white noise for classroom
                return self._generate_white_noise(duration_ms, volume=-30)
            
            elif background_type == "cafe":
                # Generate ambient cafe sounds
                base_noise = self._generate_white_noise(duration_ms, volume=-25)
                
                # Add some subtle variations for cafe atmosphere
                for _ in range(random.randint(3, 7)):
                    start = random.randint(0, max(1, duration_ms - 2000))
                    # Coffee machine sounds (higher frequency)
                    tone = Sine(random.randint(300, 1200)).to_audio_segment(duration=random.randint(200, 800))
                    tone = tone - 35  # Very quiet
                    base_noise = base_noise.overlay(tone, position=start)
                
                # Add some lower frequency rumble
                for _ in range(random.randint(2, 4)):
                    start = random.randint(0, max(1, duration_ms - 3000))
                    rumble = Sine(random.randint(80, 200)).to_audio_segment(duration=random.randint(1000, 3000))
                    rumble = rumble - 40
                    base_noise = base_noise.overlay(rumble, position=start)
                
                return base_noise
            
            elif background_type == "park":
                # Generate nature-like sounds
                base_noise = self._generate_white_noise(duration_ms, volume=-28)
                
                # Add bird-like chirps
                for _ in range(random.randint(4, 8)):
                    start = random.randint(0, max(1, duration_ms - 1000))
                    # Bird chirp (high frequency, short duration)
                    chirp = Sine(random.randint(1500, 3000)).to_audio_segment(duration=random.randint(100, 400))
                    chirp = chirp - 32
                    base_noise = base_noise.overlay(chirp, position=start)
                
                # Add wind-like sounds (low frequency)
                for _ in range(random.randint(2, 4)):
                    start = random.randint(0, max(1, duration_ms - 4000))
                    wind = Sine(random.randint(50, 150)).to_audio_segment(duration=random.randint(2000, 4000))
                    wind = wind - 38
                    base_noise = base_noise.overlay(wind, position=start)
                
                return base_noise
            
            elif background_type == "home":
                # Very subtle home environment sounds
                base_noise = self._generate_white_noise(duration_ms, volume=-35)
                
                # Add occasional household sounds
                for _ in range(random.randint(1, 3)):
                    start = random.randint(0, max(1, duration_ms - 1500))
                    # Subtle household sounds
                    sound = Sine(random.randint(200, 800)).to_audio_segment(duration=random.randint(300, 1000))
                    sound = sound - 38
                    base_noise = base_noise.overlay(sound, position=start)
                
                return base_noise
            
            else:
                # Default quiet background
                return self._generate_white_noise(duration_ms, volume=-40)
                
        except Exception as e:
            print(f"Background generation error: {e}")
            # If background generation fails, return silence
            return AudioSegment.silent(duration=duration_ms)
    
    def _generate_white_noise(self, duration_ms, volume=-30):
        """
        Generate white noise
        
        Args:
            duration_ms (int): Duration in milliseconds
            volume (int): Volume in dB
            
        Returns:
            AudioSegment: White noise audio segment
        """
        try:
            # Create white noise by overlaying multiple sine waves at different frequencies
            noise = AudioSegment.silent(duration=duration_ms)
            
            # Generate noise across different frequency ranges
            for freq in range(100, 2000, 150):
                amplitude_variation = random.uniform(0.5, 1.0)
                sine_wave = Sine(freq).to_audio_segment(duration=duration_ms)
                sine_wave = sine_wave + volume - 15 + (amplitude_variation * 5)  # Add some variation
                noise = noise.overlay(sine_wave)
            
            # Apply final volume adjustment
            noise = noise + volume
            
            return noise
            
        except Exception as e:
            print(f"White noise generation error: {e}")
            return AudioSegment.silent(duration=duration_ms)
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        self.cleanup()