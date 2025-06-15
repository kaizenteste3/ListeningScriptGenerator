
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
                
                # Create synthesizer
                temp_file = os.path.join(self.temp_dir, f"{speaker}_{i}.wav")
                audio_config = speechsdk.audio.AudioOutputConfig(filename=temp_file)
                synthesizer = speechsdk.SpeechSynthesizer(
                    speech_config=self.speech_config, 
                    audio_config=audio_config
                )
                
                # Synthesize speech
                result = synthesizer.speak_text_async(text).get()
                
                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    # Load the generated audio file
                    audio_segment = AudioSegment.from_wav(temp_file)
                    
                    # Add pause between speakers (1 second)
                    if combined_segments:
                        combined_segments.append(AudioSegment.silent(duration=1000))
                    
                    combined_segments.append(audio_segment)
                    
                    # Store individual file path
                    individual_files[f"{speaker}_{i}"] = temp_file
                    
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
            
            # Export combined audio
            combined_file = os.path.join(self.temp_dir, "combined_conversation.wav")
            combined_audio.export(combined_file, format="wav")
            
            return {
                "combined": combined_file,
                "individual": individual_files
            }
            
        except Exception as e:
            raise Exception(f"Failed to generate audio with Azure Speech Services: {e}")
    
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
                # Generate soft ambient noise
                return self._generate_ambient_noise(duration_ms, volume=-20)
            
            elif background_type == "cafe":
                # Generate gentle ambient sound with some variation
                base_noise = self._generate_ambient_noise(duration_ms, volume=-18)
                # Add some subtle variations (coffee shop sounds)
                variations = []
                for _ in range(3):
                    start = random.randint(0, max(1, duration_ms - 2000))
                    tone = Sine(random.randint(200, 600)).to_audio_segment(duration=800)
                    tone = tone - 25  # Quiet background chatter simulation
                    variations.append((start, tone))
                
                for start, tone in variations:
                    base_noise = base_noise.overlay(tone, position=start)
                
                return base_noise
            
            elif background_type == "park":
                # Generate nature-like sounds
                base_noise = self._generate_ambient_noise(duration_ms, volume=-22)
                # Add some bird-like sounds
                for _ in range(2):
                    start = random.randint(0, max(1, duration_ms - 1000))
                    chirp = Sine(random.randint(800, 1500)).to_audio_segment(duration=300)
                    chirp = chirp - 20  # Bird sounds
                    base_noise = base_noise.overlay(chirp, position=start)
                
                return base_noise
            
            elif background_type == "home":
                # Subtle home background
                return self._generate_ambient_noise(duration_ms, volume=-25)
            
            else:
                # Default quiet background
                return self._generate_ambient_noise(duration_ms, volume=-30)
                
        except Exception as e:
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
