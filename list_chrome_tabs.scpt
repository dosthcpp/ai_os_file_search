tell application "Google Chrome"
    set windowList to windows
    set resultText to ""
    repeat with theWindow in windowList
        set tabList to tabs of theWindow
        repeat with theTab in tabList
            set resultText to resultText & "Title: " & title of theTab & " | URL: " & URL of theTab & "\n"
        end repeat
    end repeat
    return resultText
end tell