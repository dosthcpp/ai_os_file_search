on run
    tell application "Mail"
        try
            set targetAccount to account "Exchange"
            set inboxMailbox to mailbox "받은 편지함" of targetAccount
            
            set yesterday to (current date) - (1 * days)
            
            set resultText to ""
            set inboxMessages to (messages of inboxMailbox)
            
            repeat with msg in inboxMessages
                if date received of msg > yesterday then
                    set resultText to resultText & "Subject: " & (subject of msg) & "\n"
                    set resultText to resultText & "Sender: " & (sender of msg) & "\n"
                    set resultText to resultText & "Date: " & (date received of msg as string) & "\n"
                    set resultText to resultText & "Read Status: " & (read status of msg as string) & "\n"
                    set resultText to resultText & "Content: " & (content of msg) & "\n"
                    set resultText to resultText & "---" & "\n"
                end if
            end repeat
            
            if resultText is "" then
                return "No messages found in the last 24 hours."
            end if
            return resultText
        on error errMsg
            return "Error: " & errMsg
        end try
    end tell
end run