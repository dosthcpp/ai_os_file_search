on run
    tell application "Mail"
        set unreadMessages to ""
        try
            set targetAccount to account "Exchange"
            set inboxMailbox to mailbox "받은 편지함" of targetAccount
            set inboxMessages to (messages of inboxMailbox whose read status is false)
            
            set yesterday to (current date) - (1 * days)
            
            set resultText to ""
            repeat with msg in inboxMessages
                if date received of msg > yesterday then
                    set resultText to resultText & "Subject: " & (subject of msg) & "\n"
                    set resultText to resultText & "Sender: " & (sender of msg) & "\n"
                    set resultText to resultText & "Date: " & (date received of msg as string) & "\n"
                    set resultText to resultText & "Content: " & (content of msg) & "\n"
                    set resultText to resultText & "---" & "\n"
                end if
            end repeat
            if resultText is "" then
                return "No unread messages found in the last 24 hours."
            end if
            return resultText
        on error errMsg
            return "Error: " & errMsg
        end try
        
        if unreadMessages is "" then
            return "No unread messages in the last 24 hours."
        else
            return unreadMessages
        end if
    end tell
end run