import os
import tempfile
from gtts import gTTS
from pydub import AudioSegment
from pydub.generators import Sine
import random
import time

class AudioGenerator:
    def __init__(self):
        """Initialize the audio generator"""
        self.temp_dir = tempfile.mkdtemp()
        
    def generate_conversation_audio(self, conversation, add_background=False, background_type=None):
        """
        Generate audio files from conversation script
        
        Args:
            conversation (list): List of conversation lines with speaker and text
            add_background (bool): Whether to add background audio
            background_type (str): Type of background audio to add
            
        Returns:
            dict: Dictionary containing paths to generated audio files
        """
        try:
            individual_files = {}
            combined_segments = []
            
            # Generate individual audio files for each speaker line
            for i, line in enumerate(conversation):
                speaker = line.get('speaker', f'Speaker{i}')
                text = line.get('text', '')
                
                if not text.strip():
                    continue
                
                # Create TTS audio with retry logic and better error handling
                max_retries = 3
                retry_delay = 3
                temp_file = os.path.join(self.temp_dir, f"{speaker}_{i}.mp3")
                
                success = False
                for attempt in range(max_retries):
                    try:
                        # Add small delay between requests to avoid rate limiting
                        if attempt > 0:
                            time.sleep(retry_delay + random.uniform(1, 3))
                        
                        tts = gTTS(text=text, lang='en', slow=False, timeout=30)
                        tts.save(temp_file)
                        success = True
                        break
                    except Exception as e:
                        error_str = str(e).lower()
                        if "429" in error_str or "too many requests" in error_str:
                            if attempt < max_retries - 1:
                                wait_time = retry_delay * (2 ** attempt) + random.uniform(2, 5)
                                time.sleep(wait_time)
                                continue
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        else:
                            raise Exception(f"TTS service temporarily unavailable after {max_retries} attempts. Error: {str(e)}")
                
                if not success:
                    raise Exception("Failed to generate audio after all retry attempts")
                
                # Convert to AudioSegment for processing
                audio_segment = AudioSegment.from_mp3(temp_file)
                
                # Add pause between speakers (1 second)
                if combined_segments:
                    combined_segments.append(AudioSegment.silent(duration=1000))
                
                combined_segments.append(audio_segment)
                
                # Add a small delay between TTS requests to avoid rate limiting
                time.sleep(0.5)
                
                # Store individual file path
                individual_wav = os.path.join(self.temp_dir, f"{speaker}_{i}.wav")
                audio_segment.export(individual_wav, format="wav")
                individual_files[f"{speaker}_{i}"] = individual_wav
                
                # Clean up temp MP3 file
                os.remove(temp_file)
            
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
                # Mix background at lower volume
                combined_audio = combined_audio.overlay(background_audio - 20)
            
            # Export combined audio
            combined_file = os.path.join(self.temp_dir, "combined_conversation.wav")
            combined_audio.export(combined_file, format="wav")
            
            return {
                "combined": combined_file,
                "individual": individual_files
            }
            
        except Exception as e:
            raise Exception(f"Failed to generate audio: {e}")
    
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
            if background_type == "classroom":
                # Generate soft white noise
                return self._generate_white_noise(duration_ms, volume=-30)
            
            elif background_type == "cafe":
                # Generate gentle ambient sound with some variation
                base_noise = self._generate_white_noise(duration_ms, volume=-25)
                # Add some subtle variations
                variations = []
                for _ in range(5):
                    start = random.randint(0, max(1, duration_ms - 2000))
                    tone = Sine(random.randint(200, 800)).to_audio_segment(duration=500)
                    tone = tone - 35  # Very quiet
                    variations.append((start, tone))
                
                for start, tone in variations:
                    base_noise = base_noise.overlay(tone, position=start)
                
                return base_noise
            
            elif background_type == "park":
                # Generate nature-like sounds (simplified)
                base_noise = self._generate_white_noise(duration_ms, volume=-28)
                # Add some bird-like sounds (very simplified)
                for _ in range(3):
                    start = random.randint(0, max(1, duration_ms - 1000))
                    chirp = Sine(random.randint(1000, 2000)).to_audio_segment(duration=200)
                    chirp = chirp - 30
                    base_noise = base_noise.overlay(chirp, position=start)
                
                return base_noise
            
            elif background_type == "home":
                # Very subtle background
                return self._generate_white_noise(duration_ms, volume=-35)
            
            else:
                # Default quiet background
                return self._generate_white_noise(duration_ms, volume=-40)
                
        except Exception as e:
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
        # Create white noise by overlaying multiple sine waves
        noise = AudioSegment.silent(duration=duration_ms)
        
        for freq in range(100, 2000, 100):
            sine_wave = Sine(freq).to_audio_segment(duration=duration_ms)
            sine_wave = sine_wave + volume - 10  # Make it quieter
            noise = noise.overlay(sine_wave)
        
        return noise + volume
    
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
