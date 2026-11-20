import shutil, subprocess, sys
from conftest import FIX, TOOLS
sys.path.insert(0, str(TOOLS))
import assemble_clips as asm
import scene_harness as h

def tone(path, seconds):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
                    "-c:a", "libmp3lame", str(path)], check=True)

def test_per_clip_sync_bounds_drift(tmp_path):
    d = tmp_path / "s01"; shutil.copytree(FIX / "scene_s01", d); h.compose(d, "s01")
    r = h.render(d, "s01", None, "l"); assert r["ok"]
    secs = {s["name"]: d / s["path"] for s in r["sections"]}
    # clip_01 video ≈2.5s with 3.0s narration (video must be padded); clip_02 ≈2.5s with 1.5s narration (audio padded)
    tone(tmp_path / "a1.mp3", 3.0); tone(tmp_path / "a2.mp3", 1.5); tone(tmp_path / "a3.mp3", 0.4)
    man = {"scenes": [{"scene_id": "s01", "clips": [
        {"clip_id": "s01c01", "video": secs["clip_01"], "audio": tmp_path / "a1.mp3"},
        {"clip_id": "s01c02", "video": secs["clip_02"], "audio": tmp_path / "a2.mp3", "lead_in": 0.2},
        {"clip_id": "s01c03", "video": secs["clip_03"], "audio": tmp_path / "a3.mp3"}]}]}
    rep = asm.assemble(man, tmp_path / "final.mp4", tmp_path / "work", loudnorm=True)
    c1, c2 = rep["clips"]["s01c01"], rep["clips"]["s01c02"]
    assert c1["video_padded_s"] > 0.3 and c1["out_s"] >= 3.0          # narration never cut off
    assert c2["audio_padded_s"] > 0.5 and abs(c2["out_s"] - c2["video_s"]) < 0.1
    assert abs(rep["final_s"] - rep["sum_clips_s"]) < 0.2              # no drift accumulated by concat
