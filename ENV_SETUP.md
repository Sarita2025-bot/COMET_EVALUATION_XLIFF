# Hugging Face Token Setup

This project requires a Hugging Face token to access the COMET-QE models. You have three options:

## Option 1: Using .env File (Recommended for Development)

1. **Create a `.env` file** in the project root directory:
   ```
   HF_TOKEN=your_huggingface_token_here
   ```

2. **Get your Hugging Face token:**
   - Visit: https://huggingface.co/settings/tokens
   - Create a new token (or use an existing one)
   - Copy the token

3. **Add the token to your `.env` file:**
   ```
   HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

4. **The `.env` file is already in `.gitignore`** so it won't be committed to version control.

5. **Install python-dotenv** (if not already installed):
   ```powershell
   pip install python-dotenv
   ```

## Option 2: Using Environment Variable

Set the `HF_TOKEN` environment variable in your system:

**Windows PowerShell:**
```powershell
$env:HF_TOKEN="your_token_here"
```

**Windows Command Prompt:**
```cmd
set HF_TOKEN=your_token_here
```

**Linux/Mac:**
```bash
export HF_TOKEN=your_token_here
```

## Option 3: Using Hugging Face CLI (Simplest)

1. **Install Hugging Face CLI:**
   ```powershell
   pip install huggingface_hub
   ```

2. **Login:**
   ```powershell
   hf auth login
   ```

3. This stores your token securely in Hugging Face's config file. No need for .env file!

## Notes

- The `.env` file approach (Option 1) is best for local development
- The CLI approach (Option 3) is simplest and works globally on your machine
- Environment variables (Option 2) are useful for CI/CD or Docker containers
- The script will automatically use whichever method you've configured

