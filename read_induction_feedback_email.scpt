on run
    tell application "Mail"
        try
            set targetAccount to account "Exchange"
            set inboxMailbox to mailbox "받은 편지함" of targetAccount
            set inboxMessages to (messages of inboxMailbox)
            
            repeat with msg in inboxMessages
                if (subject of msg) contains "Brett Drury has given feedback for assignment Induction Assignment" then
                    return content of msg
                end if
            end repeat
            
            return "Message not found."
        on error errMsg
            return "Error: " & errMsg
        end try
    end tell
end run