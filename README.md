# Behavioral Biometrics for Continuous User Authentication (Keystroke Dynamics)

Setup:   pip install -r requirements.txt
Offline: python train.py        # one-class SVM per CMU subject -> profiles/cmu_*.joblib
         python evaluate.py     # hold vs digraph vs trigraph: AUC / EER, saves roc.png
Live:    streamlit run app.py   # 1. Enroll (retype password 5-15x)  2. Live session

Files: features.py (hold/digraph/trigraph) | model.py (OCSVM + thresholds + tiers)
       components/keystroke/index.html (browser keydown/keyup capture)

Deploy (public web, free): push this folder to a GitHub repo, then on
share.streamlit.io -> Create app -> pick the repo, branch main, file app.py -> Deploy.
Then add TURSO_DATABASE_URL and TURSO_AUTH_TOKEN under the app's Settings -> Secrets.
Only key timings are sent to the server (never which keys).

Storage: enrolled profiles and the live attempt log are kept in Turso, so they survive
restarts. Locally, copy .streamlit/secrets.toml.example to .streamlit/secrets.toml and
fill it in (that file is git-ignored; never commit the token).

Azure: see AZURE.txt


My name is Atiqul Islam Tonmoy