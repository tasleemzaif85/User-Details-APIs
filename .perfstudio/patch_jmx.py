# PerfStudio JMX parameter patcher
# Usage: python3 patch_jmx.py <script> <users> <rampup> <loops> <duration>
import re, sys

script, users, rampup, loops, duration = sys.argv[1:6]
use_duration = duration != "-1" and int(duration) > 0

with open(script, "r", encoding="utf-8") as f:
    content = f.read()

def sp(xml, name, val):
    pat = r'(<(?:string|int|long|bool)Prop\s+name="' + re.escape(name) + r'">)[^<]*'
    new, n = re.subn(pat, r'\g<1>' + str(val), xml)
    print(("  SET " if n else "  WARN ") + name + "=" + str(val))
    return new

# Fix absolute local paths -> CI workspace paths
# Strips Windows paths up to and including git-workspaces/<project>/<user>/
# so JMeter finds files relative to /workspace (the Docker-mounted repo root).
path_pattern = r'[A-Za-z]:[/\\][^\'\'"<>]*?git-workspaces[/\\][^/\\]+[/\\][^/\\]+[/\\]'
fixed_content, path_fixes = re.subn(path_pattern, '/workspace/', content)
if path_fixes:
    fixed_content = fixed_content.replace('\\', '/')
    content = fixed_content
    print("  FIXED " + str(path_fixes) + " absolute path(s) -> /workspace/")
else:
    # Fallback: old single-level structure git-workspaces/<user>/
    path_pattern_old = r'[A-Za-z]:[/\\][^\'\'"<>]*?git-workspaces[/\\][^/\\]+[/\\]'
    fixed_content, path_fixes = re.subn(path_pattern_old, '/workspace/', content)
    if path_fixes:
        fixed_content = fixed_content.replace('\\', '/')
        content = fixed_content
        print("  FIXED " + str(path_fixes) + " absolute path(s) (old structure) -> /workspace/")
    else:
        print("  No absolute paths to fix")

content = sp(content, "ThreadGroup.num_threads", users)
content = sp(content, "ThreadGroup.ramp_time", rampup)

if use_duration:
    print("  Mode: Duration " + duration + "s")
    content = sp(content, "ThreadGroup.scheduler", "true")
    content = sp(content, "ThreadGroup.duration", duration)
    content = sp(content, "LoopController.loops", "-1")
    if 'name="ThreadGroup.duration"' not in content:
        content = content.replace("</ThreadGroup>",
            '<stringProp name="ThreadGroup.duration">' + duration + '</stringProp>\n'
            '<boolProp name="ThreadGroup.scheduler">true</boolProp>\n</ThreadGroup>')
        print("  INJECTED duration+scheduler")
else:
    print("  Mode: Loops " + loops)
    content = sp(content, "ThreadGroup.scheduler", "false")
    content = sp(content, "LoopController.loops", loops)

with open(script, "w") as f:
    f.write(content)
print("Patch complete")
