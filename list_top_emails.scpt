on run
    tell application "Mail"
        try
            set targetAccount to account "Exchange"
            set inboxMailbox to mailbox "받은 편지함" of targetAccount
            set inboxMessages to (messages of inboxMailbox)
            
            set resultText to ""
            set messageCount to count of inboxMessages
            
            if messageCount is 0 then
                return "No messages in the Inbox."
            end if
            
            set limit to 5
            if messageCount < 5 then set limit to messageCount
            
            repeat with i from 1 to limit
                set msg to item i of inboxMessages
                set resultText to resultText & "Subject: " & (subject of msg) & "\n"
                set resultText to resultText & "Sender: " & (sender of msg) & "\n"
                set resultText to resultText & "Date: " & (date received of msg as string) & "\n"
                set resultText to resultText & "Read Status: " & (read status of msg as string) & "\n"
                set resultText to resultText & "---" & "\n"
            end repeat
            return resultText
        on error errMsg
            return "Error: " & errMsg
        end try
    end tell
end run