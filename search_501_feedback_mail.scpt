on run
    tell application "Mail"
        try
            set targetAccount to account "Exchange"
            set inboxMailbox to mailbox "받은 편지함" of targetAccount
            set resultText to ""
            set allMessages to (messages of inboxMailbox)
            
            repeat with msg in allMessages
                set subj to (subject of msg)
                if (subj contains "CSCK501") and (subj contains "feedback" or subj contains "Grade") then
                    set resultText to resultText & "--- Subject: " & subj & " ---\n"
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