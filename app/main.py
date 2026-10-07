
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw
import numpy as np
from detector import analyze_ela, analyze_local_consistency, inspect_metadata, assess

BG="#0f1418"; PANEL="#171e23"; BORDER="#2a343c"; TEXT="#eef3f6"; MUTED="#9aa8b3"; ACCENT="#1f8f78"

class App:
    def __init__(self, root):
        self.root=root
        root.title("Digital Document Tamper Detector")
        root.geometry("1180x850"); root.minsize(980,720); root.configure(bg=BG)
        self.original_photo=None; self.analysis_photo=None
        self.build()

    def build(self):
        tk.Label(self.root,text="DIGITAL DOCUMENT TAMPER DETECTOR",font=("Segoe UI",22,"bold"),fg=TEXT,bg=BG).pack(pady=(22,2))
        tk.Label(self.root,text="Adaptive ELA  •  Local Consistency  •  Metadata",font=("Segoe UI",10),fg=MUTED,bg=BG).pack(pady=(0,14))
        tk.Button(self.root,text="Choose Document Image",command=self.choose,font=("Segoe UI",11,"bold"),bg=ACCENT,fg="white",relief="flat",padx=22,pady=10,cursor="hand2").pack()
        self.file_label=tk.Label(self.root,text="No image selected",font=("Segoe UI",9),fg=MUTED,bg=BG); self.file_label.pack(pady=8)

        viewer=tk.Frame(self.root,bg=BG); viewer.pack(fill="both",expand=True,padx=22)
        left=self.panel(viewer,"ORIGINAL DOCUMENT"); left.pack(side="left",fill="both",expand=True,padx=(0,7))
        right=self.panel(viewer,"ANOMALY OVERLAY"); right.pack(side="left",fill="both",expand=True,padx=(7,0))
        self.original_label=tk.Label(left,text="Select an image",bg=PANEL,fg=MUTED); self.original_label.pack(fill="both",expand=True,padx=8,pady=8)
        self.analysis_label=tk.Label(right,text="Anomaly overlay will appear here",bg=PANEL,fg=MUTED); self.analysis_label.pack(fill="both",expand=True,padx=8,pady=8)

        result=tk.Frame(self.root,bg=PANEL,highlightbackground=BORDER,highlightthickness=1); result.pack(fill="x",padx=22,pady=12)
        self.status=tk.Label(result,text="Choose an image to begin",font=("Segoe UI",14,"bold"),fg=TEXT,bg=PANEL,pady=10); self.status.pack(fill="x")
        self.details=tk.Text(result,height=13,font=("Consolas",9),bg=PANEL,fg="#dce4e9",relief="flat",padx=12,pady=8); self.details.pack(fill="x"); self.details.configure(state="disabled")
        tk.Label(self.root,text="Image-forensics indicators only — not proof of authenticity, identity, or fraud.",font=("Segoe UI",8),fg="#71808b",bg=BG).pack(pady=(0,12))

    def panel(self,parent,title):
        f=tk.Frame(parent,bg=PANEL,highlightbackground=BORDER,highlightthickness=1)
        tk.Label(f,text=title,font=("Segoe UI",10,"bold"),fg=TEXT,bg=PANEL).pack(pady=(9,0))
        return f

    def choose(self):
        path=filedialog.askopenfilename(title="Select document image",filetypes=[("Image files","*.jpg *.jpeg *.png *.webp *.bmp"),("All files","*.*")])
        if path:
            try: self.analyze(path)
            except Exception as e: messagebox.showerror("Analysis failed",f"The selected image could not be analyzed.\n\n{e}")

    @staticmethod
    def fit(image,size=(520,365)):
        x=image.copy(); x.thumbnail(size); return ImageTk.PhotoImage(x)

    @staticmethod
    def overlay(original,ela_heat,local_heat,boxes):
        base=original.convert("RGB"); w,h=base.size
        e=np.asarray(ela_heat.resize((w,h)),dtype=np.float32)/255
        l=np.asarray(local_heat.resize((w,h)),dtype=np.float32)/255
        s=np.clip((0.55*e+0.45*l)*1.6,0,1)
        a=np.asarray(base,dtype=np.float32); o=a.copy()
        o[:,:,0]=np.clip(a[:,:,0]+170*s,0,255)
        o[:,:,1]=np.clip(a[:,:,1]*(1-0.45*s),0,255)
        o[:,:,2]=np.clip(a[:,:,2]*(1-0.45*s),0,255)
        out=Image.fromarray(o.astype("uint8")); d=ImageDraw.Draw(out)
        for x1,y1,x2,y2,_ in boxes[:8]:
            d.rectangle((x1,y1,x2,y2),outline=(255,70,50),width=max(2,w//500))
        return out

    def analyze(self,path):
        path=Path(path); self.file_label.config(text=str(path))
        original=Image.open(path).convert("RGB")
        ela=analyze_ela(path); local=analyze_local_consistency(path); meta=inspect_metadata(path); result=assess(ela,local,meta)
        self.original_photo=self.fit(original); self.original_label.config(image=self.original_photo,text="")
        boxes=ela["boxes"]+local["boxes"]; overlay=self.overlay(original,ela["heatmap"],local["heatmap"],boxes)
        self.analysis_photo=self.fit(overlay); self.analysis_label.config(image=self.analysis_photo,text="")
        self.status.config(text=result["status"])

        lines=[
            "CHECK 1 — ADAPTIVE ERROR LEVEL ANALYSIS",
            f"  Mean compression error  : {ela['mean_error']:.2f}",
            f"  Max compression error   : {ela['max_error']:.0f}",
            f"  High-error blocks       : {ela['suspicious_blocks']}",
            f"  ELA regions             : {ela['regions']}",
            "",
            "CHECK 2 — LOCAL CONSISTENCY",
            f"  Anomalous blocks        : {local['anomaly_blocks']}",
            f"  Local anomaly regions   : {local['regions']}",
            "",
            "CHECK 3 — FILE / METADATA",
            f"  Format                  : {meta['format']}",
            f"  Resolution              : {meta['width']} x {meta['height']}",
            f"  File size               : {meta['file_size_kb']:.1f} KB",
            f"  EXIF fields             : {meta['exif_count']}",
            "",
            f"PRIMARY EVIDENCE          : {result['evidence']}/2",
            f"ASSESSMENT LEVEL         : {result['level']}",
            "",
            "WHY"
        ]
        lines += ["  • "+x for x in result["reasons"]] or ["  • No clustered anomaly was strong enough for the primary checks."]
        lines += ["","Metadata is reported separately and is NOT treated as proof of editing.","Normal scans, screenshots, resizing and JPEG recompression can create anomalies."]
        self.details.configure(state="normal"); self.details.delete("1.0","end"); self.details.insert("1.0","\n".join(lines)); self.details.configure(state="disabled")

if __name__=="__main__":
    root=tk.Tk(); App(root); root.mainloop()
