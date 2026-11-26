import subprocess, os, glob, sys
sys.path.insert(0, "/home/claude/work"); from musikbox_klicks import start
M = {"0dcf49a3":("You're The Voice","John Farnham"),"48e7eb55":("Save Tonight","Eagle-Eye Cherry"),"b91d5a1d":("Katchi","Ofenbach"),
"0a7f18ff":("Push It",""),"15f69a78":("She Wolf",""),"c3573932":("Stand By Me","Oasis"),"74a4f50a":("Unconditionally","Katy Perry"),
"576af5e9":("Breakdown Tuesday",""),"a05888a7":("Danger Zone","Kenny Loggins"),"70566056":("All Star","Smash Mouth"),"21de505d":("Song 2","Blur"),
"0727b5ca":("Just Can't Get Enough","Depeche Mode"),"c928acd2":("Freed From Desire","Gala"),"2aca8a2a":("The Middle",""),"12438f2b":("Don't Look Back In Anger","Oasis"),
"c445155b":("Dancing With Tears In My Eyes","Ultravox"),"73be0c78":("Titanium","David Guetta feat. Sia"),"4ff8935e":("Don't Stop Believin'","Journey"),
"cbc449f4":("Don't Bring Me Down","Electric Light Orchestra"),"8b20d26a":("Crying At The Discoteque","Alcazar"),"9ae6147b":("Wheels",""),
"cb733f01":("Living On My Own","Freddie Mercury"),"fcd1eccf":("Larger Than Life","Backstreet Boys"),"6edeb7e9":("Come And Get Your Love","Redbone")}
for p,(t,sub) in M.items():
    f = glob.glob(f"/mnt/user-data/uploads/{p}-*.mp3")[0]; s = start(f); out = f"/home/claude/work/mb/{p}.wav"
    subprocess.run(["ffmpeg","-v","error","-y","-ss",f"{s:.3f}","-i",f,"-af","afade=t=in:d=0.02","-c:a","pcm_s16le",out],check=True)
    args = ["python3","/home/claude/mery-gueueger.github.io/werkzeuge/archiv.py",out,t] + ([sub] if sub else [])
    r = subprocess.run(args, capture_output=True, text=True); print(t, round(s,2), "ok" if r.returncode==0 else r.stderr[-200:])
