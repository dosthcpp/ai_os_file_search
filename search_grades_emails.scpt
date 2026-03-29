on run
    tell application "Mail"
        try
            set targetAccount to account "Exchange"
            set inboxMailbox to mailbox "받은 편지함" of targetAccount
            
            set resultText to ""
            set inboxMessages to (messages of inboxMailbox)
            set msgCount to count of inboxMessages
            
            set limit to 30
            if msgCount < 30 then set limit to msgCount
            
            repeat with i from 1 to limit
                set msg to item i of inboxMessages
                set subj to (subject of msg)
                if (subj contains "Grade" or subj contains "Feedback" or subj contains "Module") then
                    set resultText to resultText & "Subject: " & subj & "\n"
                    set resultText to resultText & "Sender: " & (sender of msg) & "\n"
                    set resultText to resultText & "Date: " & (date received of msg as string) & "\n"
                    set resultText to resultText & "---" & "\n"
                end if
            end repeat
            
            return resultText
        on error errMsg
            return "Error: " & errMsg
        end try
    end tell
end run