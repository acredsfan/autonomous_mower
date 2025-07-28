# Security Configuration Guide

## ⚠️ IMPORTANT: Protecting Sensitive Information

This project handles sensitive information including:
- API keys (Google Maps, OpenAI, etc.)
- GPS coordinates and location data
- WiFi passwords and network credentials
- Personal settings and preferences

## Configuration Files

### Template Files (Safe to Commit)
- `mower/config/config.yaml.template` - Configuration template
- `config/boundary.json.template` - Boundary template
- `config/home_location.json.template` - Home location template

### User Files (NEVER Commit)
- `mower/config/config.yaml` - Your actual configuration with API keys
- `config/boundary.json` - Your actual yard boundary coordinates
- `config/home_location.json` - Your actual home coordinates
- `config/main_config_backup.json` - Contains ALL environment variables
- `data/` directory - Contains usage patterns and personal data

## Setup Instructions

1. Copy template files to create your configuration:
   ```bash
   cp mower/config/config.yaml.template mower/config/config.yaml
   cp config/boundary.json.template config/boundary.json
   cp config/home_location.json.template config/home_location.json
   ```

2. Edit your configuration files with your actual values:
   - Add your Google Maps API key to `mower/config/config.yaml`
   - Set your yard boundary in `config/boundary.json`
   - Set your home location in `config/home_location.json`

3. These files are automatically excluded by `.gitignore`

## API Key Management

### Google Maps API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Maps JavaScript API
3. Create API key with appropriate restrictions
4. Add to `mower/config/config.yaml`

### Security Best Practices
- Never commit actual configuration files
- Use environment variables for CI/CD
- Regularly rotate API keys
- Restrict API key usage by domain/IP where possible
- Monitor API key usage for unusual activity

## If You Accidentally Commit Sensitive Data

1. **Immediately** rotate all exposed credentials
2. Remove files from git history:
   ```bash
   git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch SENSITIVE_FILE' --prune-empty --tag-name-filter cat -- --all
   ```
3. Force push to overwrite remote history (if safe to do so)
4. Contact your API providers to revoke exposed keys

## File Structure Safety

```
mower/
├── config/
│   ├── config.yaml.template    ✅ Safe to commit
│   └── config.yaml            ❌ Contains API keys - EXCLUDED
config/
├── boundary.json.template     ✅ Safe to commit  
├── boundary.json             ❌ Contains your location - EXCLUDED
├── home_location.json.template ✅ Safe to commit
└── home_location.json        ❌ Contains your location - EXCLUDED
data/                         ❌ Contains usage patterns - EXCLUDED
```
