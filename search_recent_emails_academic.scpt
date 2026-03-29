on run
    tell application "Mail"
        try
            set targetAccount to account "Exchange"
            set inboxMailbox to mailbox "받은 편지함" of targetAccount
            
            set resultText to ""
            set inboxMessages to (messages of inboxMailbox)
            set msgCount to count of inboxMessages
            
            set limit to 50
            if msgCount < 50 then set limit to msgCount
            
            repeat with i from 1 to limit
                set msg to item i of inboxMessages
                set subj to (subject of msg)
                set cnt to (content of msg)
                if (subj contains "503" or subj contains "501" or subj contains "induction" or subj contains "CSCK") or (cnt contains "503" or cnt contains "501" or cnt contains "induction" or cnt contains "CSCK") then
                    set resultText to resultText & "Subject: " & subj & "\n"
                    set resultText to resultText & "Sender: " & (sender of msg) & "\n"
                    set resultText to resultText & "Date: " & (date received of msg as string) & "\n"
                    -- set resultText to resultText & "Content: " & cnt & "\n"
                    set resultText to resultText & "---" & "\n"
                end if
            end repeat
            
            if resultText is "" then
                return "No matching messages found in the last 50 messages."
            end if
            return resultText
        on error errMsg
            return "Error: " & errMsg
        end try
    end tell
end run