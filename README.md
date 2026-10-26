# Behavioral Biometrics for Continuous User Authentication (Keystroke Dynamics)

Setup:   pip install -r requirements.txt
Offline: python train.py        # one-class SVM per CMU subject -> profiles/cmu_*.joblib
         python evaluate.py     # hold vs digraph vs trigraph: AUC / EER, saves roc.png
Live:    streamlit run app.py   # 1. Enroll (retype password 5-15x)  2. Live session

Files: features.py (hold/digraph/trigraph) | model.py (OCSVM + thresholds + tiers)
       components/keystroke/index.html (browser keydown/keyup capture)

Deploy (public web, free): push this folder to a GitHub repo, then on
share.streamlit.io -> Create app -> pick the repo, branch main, file app.py -> Deploy.
Only key timings are sent to the server (never which keys). Profiles live in
profiles/ on the server and are wiped when the app restarts.

Azure: see AZURE.txt


My name is Atiqul Islam Tonmoy