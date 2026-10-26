"""Run with: streamlit run app.py"""
import io
import re
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from parser import parse_upload, parse_manifest, terms_from_query, text_matches

st.set_page_config(page_title='LikedLens | Instagram Like Search', page_icon='🔎', layout='wide')
st.markdown('''<style>
.block-container{max-width:1250px;padding-top:2rem}
.hero{border-radius:18px;background:linear-gradient(110deg,#34205d,#a23d76);padding:28px;color:white;margin-bottom:18px}
.hero h1{color:white;margin:0;font-size:2.2rem}.hero p{color:#f5eaff;margin-bottom:0}
.muted{color:#777;font-size:.9rem}
</style>''', unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>🔎 LikedLens</h1><p>Find Instagram posts and Reels you liked — using your own exported data.</p></div>', unsafe_allow_html=True)

@st.cache_resource(show_spinner='Loading local image model (first launch may download model weights)…')
def visual_model():
    from analysis_engine import get_visual_model
    return get_visual_model()

@st.cache_resource(show_spinner='Loading local speech model (first launch may download weights)…')
def audio_model():
    from analysis_engine import get_audio_model
    return get_audio_model()


def shortcode(url):
    return url.rstrip('/').split('/')[-1].casefold()


def assign_media(item, media):
    named = item.get('media_file', '').replace('\\', '/').split('/')[-1].casefold()
    key = shortcode(item['url'])
    if named and named in media:
        return named
    for name in media:
        if key in Path(name).stem.casefold():
            return name
    return ''


def show_item(item, media):
    name = item.get('_attached', '')
    if name and Path(name).suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}:
        try:
            st.image(Image.open(io.BytesIO(media[name])), use_container_width=True)
        except Exception:
            st.info('Preview unavailable')
    elif name and Path(name).suffix.lower() in {'.mp4', '.mov', '.m4v', '.webm'}:
        st.video(media[name])
    else:
        st.markdown('🎬 **Reel**' if item['type'] == 'reel' else '🖼️ **Post**')
        st.caption('No local thumbnail available')
    st.markdown(f"**{item['type'].title()}**")
    st.write((item['caption'] or 'No caption in export')[:350])
    if item['hashtags']:
        st.caption(item['hashtags'][:180])
    if item.get('_visual_score') is not None:
        st.caption(f"Visual similarity: {item['_visual_score']:.2f}")
    if item.get('_audio_hit'):
        st.caption('🎤 Matched spoken audio')
    if item['liked_at']:
        st.caption(f"Liked timestamp: {item['liked_at']}")
    st.link_button('Open on Instagram ↗', item['url'], use_container_width=True)

with st.sidebar:
    st.header('1 · Import liked activity')
    st.markdown('Instagram → **Accounts Center → Your information and permissions → Download your information**. Choose likes/activity in JSON format if available. Menu names can change.')
    export = st.file_uploader('Instagram export ZIP or liked_posts JSON/HTML/CSV', type=['zip', 'json', 'csv', 'html', 'htm'])
    st.caption('Files are processed in this local Streamlit process. Do not deploy this app publicly without access control, file limits, and storage protections.')
    manifest = st.file_uploader('Optional enriched CSV (captions / media mapping)', type=['csv'], key='manifest')
    st.header('2 · Attach your own media (optional)')
    uploaded_media = st.file_uploader('Images, videos and audio you own or are authorized to use',
                                      type=['jpg','jpeg','png','webp','mp4','mov','m4v','webm','wav','mp3','m4a','ogg'],
                                      accept_multiple_files=True)
    st.caption('Filename should contain the Instagram shortcode (e.g. Cxyz123.mp4), or specify media_file in the enriched CSV.')
    st.divider()
    st.info('No Instagram password, tokens, browser cookies, scraping, or automatic download of other users’ media.')

items = []
if export is not None:
    try:
        items = parse_upload(export.name, export.getvalue())
    except Exception as exc:
        st.error(f'Could not parse import: {exc}')

if manifest is not None:
    try:
        enrichment = parse_manifest(manifest.getvalue())
        by_url = {item['url']: item for item in items}
        for row in enrichment:
            if row['url'] in by_url:
                for field in ('type', 'caption', 'hashtags', 'media_file'):
                    if row.get(field):
                        by_url[row['url']][field] = row[field]
            else:
                by_url[row['url']] = row
        items = list(by_url.values())
    except Exception as exc:
        st.error(f'Could not read enriched CSV: {exc}')

media = {}
for uploaded in uploaded_media or []:
    if uploaded.size > 125 * 1024 * 1024:
        st.warning(f'Skipping oversized media: {uploaded.name}')
        continue
    media[Path(uploaded.name).name.casefold()] = uploaded.getvalue()

for item in items:
    item['_attached'] = assign_media(item, media)

c1,c2,c3 = st.columns(3)
c1.metric('Imported likes',len(items))
c2.metric('Reels',sum(i['type']=='reel' for i in items))
c3.metric('Attached media',sum(bool(i['_attached']) for i in items))
if not items:
    st.info('Start by uploading your Instagram liked-posts export, or a CSV with the column `url` (and optional caption, type, hashtags, media_file).')
    st.dataframe(pd.DataFrame([{'url':'https://www.instagram.com/reel/EXAMPLE123/', 'type':'reel', 'caption':'A short recipe for biryani', 'hashtags':'#cooking #food', 'media_file':'EXAMPLE123.mp4'}]), hide_index=True)
    st.stop()

st.header('Search liked content')
query = st.text_input('Keywords or hashtags', placeholder='biryani, #travel, beaches')
a,b,c = st.columns([1,1,1])
with a:
    kind = st.selectbox('Content type', ['Both', 'Reels', 'Posts'])
with b:
    match_mode = st.selectbox('Multiple keyword rule', ['Match any', 'Match all'])
with c:
    search_mode = st.selectbox('Search method', ['Captions & hashtags', 'Captions + local media AI'])

st.caption('Separate phrases with commas; without commas, each word is a separate keyword. #tags work as either hashtag or word matches.')
terms = terms_from_query(query)
threshold = 0.23
check_audio = False
if search_mode == 'Captions + local media AI':
    threshold = st.slider('Minimum visual similarity (heuristic)', 0.10, 0.60, 0.23, 0.01)
    check_audio = st.checkbox('Also transcribe speech in locally attached video/audio (requires FFmpeg)', value=False)
    st.caption('AI requires requirements-ai.txt and attached media. Visual similarity is approximate, not guaranteed. First use may download model files.')

filtered = [item.copy() for item in items if kind == 'Both' or item['type'] == ('reel' if kind == 'Reels' else 'post')]

if search_mode == 'Captions & hashtags' or not terms:
    matches = [i for i in filtered if text_matches(i, terms, match_all=match_mode=='Match all')]
else:
    if st.button('Run AI search', type='primary'):
        try:
            from analysis_engine import image_similarity, transcribe_media, IMAGE_EXTS, VIDEO_EXTS, AUDIO_EXTS
            has_visual = any(i['_attached'] and Path(i['_attached']).suffix.lower() in IMAGE_EXTS | VIDEO_EXTS for i in filtered)
            vm = visual_model() if has_visual else None
            am = audio_model() if check_audio else None
            matches = []
            bar = st.progress(0)
            for idx, item in enumerate(filtered):
                text_hit = text_matches(item, terms, match_all=match_mode=='Match all')
                name = item['_attached']
                visual_score, audio_hit = None, False
                if name and vm and Path(name).suffix.lower() in IMAGE_EXTS | VIDEO_EXTS:
                    try:
                        visual_score = image_similarity(name, media[name], terms, vm)
                    except Exception as exc:
                        st.warning(f'Cannot process {name}: {exc}')
                if name and am and Path(name).suffix.lower() in VIDEO_EXTS | AUDIO_EXTS:
                    try:
                        transcript = transcribe_media(name, media[name], am)
                        audio_hit = text_matches({'caption':transcript,'hashtags':''},terms, match_all=match_mode=='Match all')
                    except Exception as exc:
                        st.warning(f'Cannot transcribe {name}: {exc}')
                item['_visual_score'] = visual_score
                item['_audio_hit'] = audio_hit
                if text_hit or (visual_score is not None and visual_score >= threshold) or audio_hit:
                    matches.append(item)
                bar.progress((idx+1)/max(len(filtered),1))
            st.session_state['ai_results'] = matches
            st.session_state['ai_signature'] = (query,kind,match_mode,threshold,check_audio,len(items),tuple(media))
        except ImportError:
            st.error('AI dependencies missing. Run: pip install -r requirements-ai.txt')
    signature = (query,kind,match_mode,threshold,check_audio,len(items),tuple(media))
    matches = st.session_state.get('ai_results', []) if st.session_state.get('ai_signature') == signature else []
    if not matches:
        st.caption('Click Run AI search to calculate results. Empty results may also mean no match.')

st.subheader(f'{len(matches)} matching item(s)')
if matches:
    export_csv = pd.DataFrame([{k:i.get(k,'') for k in ['url','type','caption','hashtags','liked_at','media_file']} for i in matches]).to_csv(index=False).encode('utf-8-sig')
    st.download_button('Download results CSV', export_csv, 'liked_matches.csv', 'text/csv')
    cols = st.columns(3)
    for index, item in enumerate(matches):
        with cols[index % 3]:
            with st.container(border=True):
                show_item(item, media)
else:
    st.info('No matches in the currently available data. Exports often contain URLs but not captions or original media; add your own metadata/media for deeper searches.')

with st.expander('Privacy and known limitations'):
    st.markdown('''- Instagram's supported API does **not** offer an endpoint to import all content a person liked. This app therefore **does not implement Instagram OAuth/login** or pretend that login would provide that permission.
- Export formats change. Items lacking a supported Instagram URL cannot be linked. A `/p/` link alone does not reliably distinguish every Reel from a post; set `type` in your own CSV to correct it.
- Most Instagram like activity exports contain metadata/links, not creators' full captions, images, video, or audio. This app does not retrieve that content automatically.
- For AI, attach media you legally possess. Visual analysis samples up to 8 frames per video, and optional speech transcription only detects spoken words; it does not identify music by melody or perform full audio event classification.
- Run on localhost for personal use. Uploaded files stay in the application's process memory while the session runs; model downloads may contact model providers on first use.
''')
