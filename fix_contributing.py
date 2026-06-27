content = open('CONTRIBUTING.md', encoding='utf-8').read()

windows_section = """
## Windows

Windows requires a few extra steps. Follow this section carefully.

### Step 1 - Verify Python is installed

Open Command Prompt or PowerShell and run:

```powershell
python --version
```

You should see `Python 3.10` or higher. If not, download it from [python.org](https://www.python.org/downloads/).

> During installation, make sure to check **"Add Python to PATH"**.

---

### Step 2 - Create a virtual environment

```powershell
python -m venv venv
```

This creates a `venv/` folder in your project directory.

---

### Step 3 - Activate the virtual environment

**Command Prompt:**

```cmd
venv\\Scripts\\activate
```

**PowerShell:**

```powershell
venv\\Scripts\\Activate.ps1
```

> If PowerShell blocks the script with an execution policy error, run this first:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Then try activating again.

Once activated, your prompt will show `(venv)` at the start.

---

### Step 4 - Install dependencies

```powershell
python -m pip install -e ".[dev]"
```

---

### Step 5 - Verify the setup

```powershell
python -c "import agentwatch; print('Setup successful')"
```

---

### Deactivating the virtual environment

```powershell
deactivate
```

---

### Common Windows Issues

| Problem | Fix |
|---|---|
| `python` not found | Re-install Python and check "Add to PATH" |
| `Activate.ps1` blocked | Run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `pip` not found inside venv | Run `python -m pip install --upgrade pip` |
| `pip install` permission error | Ensure venv is activated |
| Git line ending warnings | Run `git config --global core.autocrlf true` |

"""

# Insert after the closing ``` of Linux/macOS block, before ---
insert_after = '```\n\n---\n\n# Frontend Setup'
insert_with   = '```\n' + windows_section + '\n---\n\n# Frontend Setup'

if insert_after in content:
    content = content.replace(insert_after, insert_with, 1)
    open('CONTRIBUTING.md', 'w', encoding='utf-8').write(content)
    print('SUCCESS - Windows section added!')
else:
    print('Trying CRLF...')
    insert_after2 = '```\r\n\r\n---\r\n\r\n# Frontend Setup'
    insert_with2  = '```\r\n' + windows_section + '\r\n---\r\n\r\n# Frontend Setup'
    if insert_after2 in content:
        content = content.replace(insert_after2, insert_with2, 1)
        open('CONTRIBUTING.md', 'w', encoding='utf-8').write(content)
        print('SUCCESS - Windows section added!')
    else:
        print('FINAL ERROR - showing context around Frontend Setup:')
        idx = content.find('# Frontend Setup')
        print(repr(content[idx-50:idx+50]))
