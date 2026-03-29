on run
    tell application "Mail"
        try
            set targetAccount to account "Exchange"
            set inboxMailbox to mailbox "받은 편지함" of targetAccount
            
            set resultText to ""
            set allMessages to (messages of inboxMailbox)
            
            set limit to 500
            if (count of allMessages) < 500 then set limit to (count of allMessages)
            
            repeat with i from 1 to limit
                set msg to item i of allMessages
                set subj to (subject of msg)
                if (subj contains "CSCK501" or subj contains "CSCK503" or subj contains "Induction" or subj contains "Feedback" or subj contains "Grade") then
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