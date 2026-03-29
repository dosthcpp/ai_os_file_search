on run
    tell application "Mail"
        try
            set resultText to ""
            set allMessages to (messages of mailbox "받은 편지함" of account "Exchange")
            
            repeat with msg in allMessages
                if (sender of msg) contains "Brett Drury" then
                    set resultText to resultText & "--- Subject: " & (subject of msg) & " ---\n"
                    set resultText to resultText & "Date: " & (date received of msg as string) & "\n"
                    set resultText to resultText & "Content: " & (content of msg) & "\n"
                end if
            end repeat
            
            return resultText
        on error errMsg
            return "Error: " & errMsg
        end try
    end tell
end run