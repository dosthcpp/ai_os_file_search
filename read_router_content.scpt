tell application "Google Chrome"
    delay 5
    set currentText to execute active tab of front window javascript "document.body.innerText"
    return currentText
end tell