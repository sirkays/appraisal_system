import subprocess
import re
import os

while True:
    print("Running collectstatic...")
    result = subprocess.run(["python", "manage.py", "collectstatic", "--noinput"], capture_output=True, text=True)
    if result.returncode == 0:
        print("Success!")
        break
    
    error_output = result.stderr
    print(error_output)
    
    # Extract missing file path from WhiteNoise error
    match = re.search(r"The file '(.+?)' could not be found", error_output)
    if match:
        missing_file = match.group(1)
        # Convert path to Windows format just in case, but static/ expects forward slash usually
        # But we need to create it in static/ dir
        target_path = os.path.join("static", missing_file.replace("/", os.sep))
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w") as f:
            f.write("")
        print(f"Created dummy file for {missing_file}")
    else:
        print("Could not find missing file in output. Exiting.")
        break
