tell application "Google Chrome"
    repeat with theWindow in windows
        repeat with theTab in tabs of theWindow
            if (title of theTab contains "VLE") then
                execute theTab javascript "window.location.href = 'https://liverpool-online-study.com/course/view.php?id=3517'"
                return "Navigating to CSCK501..."
            end if
        end repeat
    end repeat
end tell