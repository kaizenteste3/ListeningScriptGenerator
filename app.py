import streamlit as st
import tempfile
import os
from script_generator import ScriptGenerator
from audio_generator import AudioGenerator

def main():
    st.set_page_config(
        page_title="中学英語リスニング教材ジェネレーター",
        page_icon="🎧",
        layout="wide"
    )
    
    st.title("🎧 中学英語リスニング教材ジェネレーター")
    st.markdown("シーンを入力して、中学英語レベルの会話スクリプトと音声ファイルを自動生成します。")
    
    # API Key input section
    st.header("🔑 API設定")
    
    col1, col2 = st.columns(2)
    
    with col1:
        api_key = st.text_input(
            "OpenAI API キーを入力してください",
            type="password",
            placeholder="sk-...",
            help="OpenAIのAPIキーが必要です。https://platform.openai.com でアカウントを作成し、APIキーを取得してください。"
        )
    
    with col2:
        azure_speech_key = st.text_input(
            "Azure Speech Services キーを入力してください",
            type="password",
            placeholder="Azure Speech Key",
            help="Azure Speech Servicesのサブスクリプションキーが必要です。"
        )
        
        azure_region = st.text_input(
            "Azure リージョンを入力してください",
            placeholder="例: japaneast",
            help="Azure Speech Servicesのリージョンを入力してください（例: japaneast, eastus）"
        )
    
    if not api_key:
        st.warning("⚠️ OpenAI API キーを入力してからスクリプト生成を行ってください。")
        st.stop()
    
    if not azure_speech_key or not azure_region:
        st.warning("⚠️ Azure Speech Services の認証情報を入力してから音声生成を行ってください。")
    
    # Initialize generators
    script_gen = ScriptGenerator(api_key)
    audio_gen = AudioGenerator(azure_speech_key, azure_region)
    
    # Sidebar for options
    st.sidebar.header("⚙️ オプション設定")
    enable_background_audio = st.sidebar.checkbox("背景音声を追加", value=False)
    background_type = st.sidebar.selectbox(
        "背景音声の種類",
        ["classroom", "cafe", "park", "home", "none"],
        disabled=not enable_background_audio
    )
    
    # Main input
    st.header("📝 シーン入力")
    scene_input = st.text_area(
        "会話のシーンや場面を入力してください",
        placeholder="例：レストランで注文をする、友達と放課後の予定を立てる、家族との夕食時の会話など",
        height=100
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        generate_button = st.button("🎯 スクリプト生成", type="primary")
    
    if generate_button and scene_input.strip():
        with st.spinner("スクリプトを生成中..."):
            try:
                # Generate script
                script_data = script_gen.generate_script(scene_input.strip())
                
                if script_data:
                    st.session_state.script_data = script_data
                    st.success("スクリプトが正常に生成されました！")
                else:
                    st.error("スクリプトの生成に失敗しました。もう一度お試しください。")
                    
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
    
    elif generate_button and not scene_input.strip():
        st.warning("シーンを入力してください。")
    
    # Display generated script
    if hasattr(st.session_state, 'script_data') and st.session_state.script_data:
        st.header("📋 生成されたスクリプト")
        
        script_data = st.session_state.script_data
        
        # Display title and situation
        st.subheader(f"タイトル: {script_data.get('title', 'Untitled')}")
        st.write(f"**場面**: {script_data.get('situation', 'No description')}")
        
        # Display conversation
        st.subheader("会話スクリプト")
        for line in script_data.get('conversation', []):
            speaker = line.get('speaker', 'Unknown')
            text = line.get('text', '')
            st.write(f"**{speaker}**: {text}")
        
        # Audio generation section
        st.header("🎵 音声生成")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            generate_audio_button = st.button("🔊 音声生成", type="secondary")
        
        if generate_audio_button:
            with st.spinner("音声ファイルを生成中..."):
                try:
                    # Generate audio
                    audio_files = audio_gen.generate_conversation_audio(
                        script_data.get('conversation', []),
                        add_background=enable_background_audio,
                        background_type=background_type if enable_background_audio else None
                    )
                    
                    if audio_files:
                        st.session_state.audio_files = audio_files
                        st.success("音声ファイルが正常に生成されました！")
                    else:
                        st.error("音声ファイルの生成に失敗しました。")
                        
                except Exception as e:
                    error_msg = str(e)
                    if "Azure Speech Services not configured" in error_msg:
                        st.error("⚠️ Azure Speech Services の認証情報が設定されていません。上記のAPIキー入力欄でAzure Speech Servicesのキーとリージョンを入力してください。")
                    elif "429" in error_msg or "Too Many Requests" in error_msg:
                        st.error("⚠️ 音声生成サービスが一時的に利用制限に達しています。数分後に再度お試しください。")
                        st.info("💡 ヒント: しばらく待ってから「音声生成」ボタンを再度クリックしてください。")
                    else:
                        st.error(f"音声生成エラー: {error_msg}")
        
        # Display audio and download options
        if hasattr(st.session_state, 'audio_files') and st.session_state.audio_files:
            st.subheader("🎧 生成された音声")
            
            audio_files = st.session_state.audio_files
            
            # Play combined conversation
            if 'combined' in audio_files:
                st.write("**完全版会話音声**")
                st.audio(audio_files['combined'])
                
                # Download button for combined audio
                with open(audio_files['combined'], 'rb') as f:
                    st.download_button(
                        label="📥 完全版音声をダウンロード",
                        data=f.read(),
                        file_name=f"conversation_{script_data.get('title', 'untitled').replace(' ', '_')}.wav",
                        mime="audio/wav"
                    )
            
            # Individual speaker audio files
            if 'individual' in audio_files:
                st.write("**個別音声ファイル**")
                for speaker, file_path in audio_files['individual'].items():
                    st.write(f"**{speaker}の音声**")
                    st.audio(file_path)
                    
                    # Download button for individual audio
                    with open(file_path, 'rb') as f:
                        st.download_button(
                            label=f"📥 {speaker}の音声をダウンロード",
                            data=f.read(),
                            file_name=f"{speaker}_{script_data.get('title', 'untitled').replace(' ', '_')}.wav",
                            mime="audio/wav",
                            key=f"download_{speaker}"
                        )
    
    # Footer
    st.markdown("---")
    st.markdown("💡 **ヒント**: より具体的なシーンを入力すると、より自然な会話が生成されます。")

if __name__ == "__main__":
    main()