on run
    tell application "Mail"
        try
            set targetAccount to account "Exchange"
            set inboxMailbox to mailbox "받은 편지함" of targetAccount
            set resultText to ""
            set inboxMessages to (messages of inboxMailbox)
            
            repeat with msg in inboxMessages
                set subj to (subject of msg)
                if (subj contains "CSCK501" or subj contains "CSCK503" or subj contains "Induction") then
                    set resultText to resultText & "Subject: " & subj & "\n"
                    set resultText to resultText & "Date: " & (date received of msg as string) & "\n"
                    set resultText to resultText & "Content: " & (content of msg) & "\n"
                    set resultText to resultText & "---" & "\n"
                end if
            end repeat
            
            return resultText
        on error errMsg
            return "Error: " & errMsg
        end try
    end tell
end run