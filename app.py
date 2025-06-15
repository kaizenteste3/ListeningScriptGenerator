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

    # ファイルアップローダー追加
    st.sidebar.header("📁 背景音声ファイルのアップロード")
    background_audio_files = st.sidebar.file_uploader(
        "背景音声ファイルをアップロードしてください（.wav形式）",
        type=["wav"],
        accept_multiple_files=True
    )

    # アップロードファイルを`background_audio`フォルダに保存
    background_audio_dir = "background_audio"
    if background_audio_files:
        if not os.path.exists(background_audio_dir):
            os.makedirs(background_audio_dir)
        for uploaded_file in background_audio_files:
            file_path = os.path.join(background_audio_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.sidebar.success(f"Uploaded: {uploaded_file.name}")

    # APIキー入力セクション
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

    # 入力がない場合は警告
    if not api_key:
        st.warning("⚠️ OpenAI API キーを入力してからスクリプト生成を行ってください。")
        st.stop()

    if not azure_speech_key or not azure_region:
        st.warning("⚠️ Azure Speech Services の認証情報を入力してから音声生成を行ってください。")

    # ジェネレーターの初期化
    script_gen = ScriptGenerator(api_key)
    audio_gen = AudioGenerator(azure_speech_key, azure_region)

    # サイドバーのオプション
    st.sidebar.header("⚙️ オプション設定")
    enable_background_audio = st.sidebar.checkbox("背景音声を追加", value=False)
    background_type = st.sidebar.selectbox(
        "背景音声の種類",
        os.listdir(background_audio_dir) if os.path.exists(background_audio_dir) else [],
        disabled=not enable_background_audio
    )

    # メイン入力
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
                # スクリプト生成
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

    # 生成されたスクリプトの表示
    if hasattr(st.session_state, 'script_data') and st.session_state.script_data:
        st.header("📋 生成されたスクリプト")

        script_data = st.session_state.script_data

        # タイトルと場面を表示
        st.subheader(f"タイトル: {script_data.get('title', 'Untitled')}")
        st.write(f"**場面**: {script_data.get('situation', 'No description')}")

        # 会話を表示
        st.subheader("会話スクリプト")
        for line in script_data.get('conversation', []):
            speaker = line.get('speaker', 'Unknown')
            text = line.get('text', '')
            st.write(f"**{speaker}**: {text}")

        # 音声生成セクション
        st.header("🎵 音声生成")

        col1, col2, col3 = st.columns(3)
        with col1:
            generate_audio_button = st.button("🔊 音声生成", type="secondary")

        if generate_audio_button:
            with st.spinner("音声ファイルを生成中..."):
                try:
                    # 音声生成
                    audio_files = audio_gen.generate_conversation_audio(
                        script_data.get('conversation', []),
                        add_background=enable_background_audio,
                        background_type=background_type if enable_background_audio else None
                    )

                    if audio_files:
                        # 音声データをセッションステートに保存
                        audio_data = {}
                        if 'combined' in audio_files and os.path.exists(audio_files['combined']):
                            with open(audio_files['combined'], 'rb') as f:
                                audio_data['combined'] = f.read()

                        individual_data = {}
                        if 'individual' in audio_files:
                            for speaker, file_path in audio_files['individual'].items():
                                if os.path.exists(file_path):
                                    with open(file_path, 'rb') as f:
                                        individual_data[speaker] = f.read()
                        audio_data['individual'] = individual_data

                        st.session_state.audio_files = audio_files
                        st.session_state.audio_data = audio_data
                        st.success("音声ファイルが正常に生成されました！")
                    else:
                        st.error("音声ファイルの生成に失敗しました。")

                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "Too Many Requests" in error_msg:
                        st.error("⚠️ 音声生成サービスが一時的に利用制限に達しています。数分後に再度お試しください。")
                        st.info("💡 ヒント: しばらく待ってから「音声生成」ボタンを再度クリックしてください。")
                    else:
                        st.error(f"音声生成エラー: {error_msg}")

        # 音声とダウンロードオプションの表示
        if hasattr(st.session_state, 'audio_data') and st.session_state.audio_data:
            st.subheader("🎧 生成された音声")

            audio_data = st.session_state.audio_data

            # 完全版会話を再生
            if 'combined' in audio_data:
                st.write("**完全版会話音声**")
                try:
                    st.audio(audio_data['combined'])

                    # 完全版音声のダウンロードボタン
                    st.download_button(
                        label="📥 完全版音声をダウンロード",
                        data=audio_data['combined'],
                        file_name=f"conversation_{script_data.get('title', 'untitled').replace(' ', '_')}.wav",
                        mime="audio/wav"
                    )
                except Exception as e:
                    st.error(f"音声の表示エラー: {e}")

            # 個別の話者音声ファイル
            if 'individual' in audio_data and audio_data['individual']:
                st.write("**個別音声ファイル**")
                for speaker, individual_audio_data in audio_data['individual'].items():
                    st.write(f"**{speaker}の音声**")
                    try:
                        st.audio(individual_audio_data)

                        # 個別音声のダウンロードボタン
                        st.download_button(
                            label=f"📥 {speaker}の音声をダウンロード",
                            data=individual_audio_data,
                            file_name=f"{speaker}_{script_data.get('title', 'untitled').replace(' ', '_')}.wav",
                            mime="audio/wav",
                            key=f"download_{speaker}"
                        )
                    except Exception as e:
                        st.error(f"{speaker}の音声表示エラー: {e}")

    # フッター
    st.markdown("---")
    st.markdown("💡 **ヒント**: より具体的なシーンを入力すると、より自然な会話が生成されます。")

if __name__ == "__main__":
    main()