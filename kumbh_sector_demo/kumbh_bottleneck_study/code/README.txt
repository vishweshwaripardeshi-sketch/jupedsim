These scripts were run from the folder that holds the Python environment (kumbh_sector_demo/), not from here.
To rerun: copy bn_sim.py, run_all.py, bn_report.py and bn_video.py into a working folder, then
  pip install -r ../../requirements.txt
  python run_all.py        # 18 runs, writes bn_runs/ (about 90 MB, not included)
  python bn_report.py      # charts + data
  python bn_video.py <run names>
run_all.py expects a virtual environment at .venv\Scripts\python.exe; edit the `py` line if yours differs.
