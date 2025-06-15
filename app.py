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
    
    # Background audio options
    st.sidebar.subheader("背景音声の設定")
    
    uploaded_background = st.sidebar.file_uploader(
        "背景音声ファイルをアップロード",
        type=["mp3", "wav"],
        disabled=not enable_background_audio,
        help="MP3またはWAV形式の背景音声ファイルをアップロードしてください"
    )
    
    # Background volume control
    background_volume = st.sidebar.slider(
        "背景音声の音量 (dB)",
        min_value=-40,
        max_value=0,
        value=-20,
        step=5,
        disabled=not enable_background_audio or not uploaded_background,
        help="背景音声の音量を調整します。負の値ほど小さくなります。"
    )
    
    # Set background_type to None since we only use uploaded files
    background_type = None
    
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
        
        # Edit mode toggle
        edit_mode = st.checkbox("✏️ スクリプトを編集", key="edit_mode")
        
        if edit_mode:
            # Editable fields
            st.subheader("スクリプト編集")
            
            # Edit title
            edited_title = st.text_input(
                "タイトル",
                value=script_data.get('title', 'Untitled'),
                key="edit_title"
            )
            
            # Edit situation
            edited_situation = st.text_area(
                "場面",
                value=script_data.get('situation', 'No description'),
                height=80,
                key="edit_situation"
            )
            
            # Edit conversation
            st.subheader("会話編集")
            edited_conversation = []
            
            for i, line in enumerate(script_data.get('conversation', [])):
                col1, col2, col3, col4 = st.columns([2, 4, 2, 1])
                
                with col1:
                    speaker = st.text_input(
                        f"話者 {i+1}",
                        value=line.get('speaker', 'Unknown'),
                        key=f"edit_speaker_{i}"
                    )
                
                with col2:
                    text = st.text_area(
                        f"台詞 {i+1}",
                        value=line.get('text', ''),
                        height=80,
                        key=f"edit_text_{i}"
                    )
                
                with col3:
                    voice_type = st.selectbox(
                        f"音声タイプ {i+1}",
                        ["男性", "女性", "若い男性", "若い女性"],
                        index=["男性", "女性", "若い男性", "若い女性"].index(line.get('voice_type', '男性')),
                        key=f"edit_voice_{i}"
                    )
                
                with col4:
                    st.write("")  # Spacing
                    if st.button("🗑️", key=f"delete_{i}", help="この行を削除"):
                        # Mark for deletion
                        if 'lines_to_delete' not in st.session_state:
                            st.session_state.lines_to_delete = []
                        st.session_state.lines_to_delete.append(i)
                        st.rerun()
                
                # Only add if not marked for deletion
                if 'lines_to_delete' not in st.session_state or i not in st.session_state.lines_to_delete:
                    edited_conversation.append({
                        'speaker': speaker,
                        'text': text,
                        'voice_type': voice_type
                    })
            
            # Add new line button
            if st.button("➕ 新しい台詞を追加"):
                if 'new_lines_count' not in st.session_state:
                    st.session_state.new_lines_count = 0
                st.session_state.new_lines_count += 1
                st.rerun()
            
            # Handle new lines
            if 'new_lines_count' in st.session_state and st.session_state.new_lines_count > 0:
                for j in range(st.session_state.new_lines_count):
                    new_idx = len(script_data.get('conversation', [])) + j
                    col1, col2, col3 = st.columns([2, 4, 2])
                    
                    with col1:
                        new_speaker = st.text_input(
                            f"新しい話者 {j+1}",
                            key=f"new_speaker_{j}"
                        )
                    
                    with col2:
                        new_text = st.text_area(
                            f"新しい台詞 {j+1}",
                            height=80,
                            key=f"new_text_{j}"
                        )
                    
                    with col3:
                        new_voice_type = st.selectbox(
                            f"音声タイプ {j+1}",
                            ["男性", "女性", "若い男性", "若い女性"],
                            key=f"new_voice_{j}"
                        )
                    
                    if new_speaker and new_text:
                        edited_conversation.append({
                            'speaker': new_speaker,
                            'text': new_text,
                            'voice_type': new_voice_type
                        })
            
            # Save changes button
            col1, col2, col3 = st.columns([1, 1, 3])
            with col1:
                if st.button("💾 変更を保存", type="primary"):
                    # Update script data
                    st.session_state.script_data = {
                        'title': edited_title,
                        'situation': edited_situation,
                        'conversation': edited_conversation
                    }
                    # Clear temporary states
                    if 'lines_to_delete' in st.session_state:
                        del st.session_state.lines_to_delete
                    if 'new_lines_count' in st.session_state:
                        del st.session_state.new_lines_count
                    # Clear any existing audio files since script changed
                    if 'audio_files' in st.session_state:
                        del st.session_state.audio_files
                    st.success("スクリプトを更新しました！")
                    st.rerun()
            
            with col2:
                if st.button("🔄 元に戻す"):
                    # Clear temporary states
                    if 'lines_to_delete' in st.session_state:
                        del st.session_state.lines_to_delete
                    if 'new_lines_count' in st.session_state:
                        del st.session_state.new_lines_count
                    st.rerun()
        
        else:
            # Display mode (read-only)
            st.subheader(f"タイトル: {script_data.get('title', 'Untitled')}")
            st.write(f"**場面**: {script_data.get('situation', 'No description')}")
            
            # Display conversation
            st.subheader("会話スクリプト")
            for line in script_data.get('conversation', []):
                speaker = line.get('speaker', 'Unknown')
                text = line.get('text', '')
                voice_type = line.get('voice_type', '男性')
                st.write(f"**{speaker}** ({voice_type}): {text}")
        
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
                        add_background=enable_background_audio and uploaded_background is not None,
                        background_type=None,
                        uploaded_background=uploaded_background if enable_background_audio else None,
                        background_volume=background_volume if enable_background_audio else -20
                    )
                    
                    if audio_files:
                        st.session_state.audio_files = audio_files
                        st.success("音声ファイルが正常に生成されました！")
                    else:
                        st.error("音声ファイルの生成に失敗しました。")
                        
                except Exception as e:
                    error_msg = str(e)
                    if "Azure Speech Services not configured" in error_msg or "SPXERR_INVALID_ARG" in error_msg:
                        st.error("⚠️ Azure Speech Services の認証情報が正しくありません。有効なAPIキーとリージョンを入力してください。")
                        st.info("💡 Azure ポータルで Speech Services リソースを作成し、正しいキーとリージョンを確認してください。")
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
                try:
                    # Check if file exists before trying to display
                    if os.path.exists(audio_files['combined']):
                        st.audio(audio_files['combined'])
                        
                        # Download button for combined audio
                        with open(audio_files['combined'], 'rb') as f:
                            st.download_button(
                                label="📥 完全版音声をダウンロード",
                                data=f.read(),
                                file_name=f"conversation_{script_data.get('title', 'untitled').replace(' ', '_')}.wav",
                                mime="audio/wav"
                            )
                    else:
                        st.error("音声ファイルが見つかりません。再度音声生成を行ってください。")
                except Exception as e:
                    st.error(f"音声ファイルの読み込みエラー: {str(e)}")
            
            # Individual speaker audio files
            if 'individual' in audio_files:
                st.write("**個別音声ファイル**")
                for speaker, file_path in audio_files['individual'].items():
                    st.write(f"**{speaker}の音声**")
                    try:
                        if os.path.exists(file_path):
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
                        else:
                            st.error(f"{speaker}の音声ファイルが見つかりません。")
                    except Exception as e:
                        st.error(f"{speaker}の音声ファイル読み込みエラー: {str(e)}")
    
    # Footer
    st.markdown("---")
    st.markdown("💡 **ヒント**: より具体的なシーンを入力すると、より自然な会話が生成されます。")

if __name__ == "__main__":
    main()