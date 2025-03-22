# Microsoft Authentication Implementation Guide

This document provides comprehensive instructions for implementing Microsoft authentication in your Minecraft launcher once your Azure application is approved.

## Prerequisites

- Approved Azure Application with permission to access the Minecraft API
- Client ID from your Azure application: `46061691-069a-400f-9cef-a636d076ccdb` 
- Redirect URL configured in your Azure application: `http://localhost:8000/callback`

## 1. Azure Application Setup

### Create Azure Application
1. Go to https://portal.azure.com/
2. Navigate to "App registrations"
3. Create a new registration with:
   - A descriptive name (without using "Minecraft", "Microsoft", etc.)
   - Account type: "Accounts in any organizational directory and personal Microsoft accounts"
   - Redirect URI: `http://localhost:8000/callback` (Web platform)

### Request Minecraft API Permission
1. Submit your application via the official form: https://aka.ms/aad-minecraft-login
2. Provide your Client ID, Tenant ID, and justification
3. Wait for approval (typically takes 1-2 weeks)

## 2. Authentication Flow Implementation

Once approved, implement this authentication flow:

```python
def microsoft_login():
    """Handle Microsoft authentication for Minecraft"""
    console.print("\n[blue]Initializing Microsoft authentication...[/blue]")
    
    try:
        # Generate a secure login with PKCE (recommended approach)
        auth_url, state, code_verifier = minecraft_launcher_lib.microsoft_account.get_secure_login_data(
            client_id=CLIENT_ID,
            redirect_uri=REDIRECT_URL
        )
        
        console.print("[yellow]Opening browser for Microsoft authentication...[/yellow]")
        
        # Reset callback data
        callback_data.clear()
        callback_data["code"] = None
        
        # Start temporary server and open browser
        with run_auth_server():
            webbrowser.open(auth_url)
            
            console.print("[blue]Waiting for Microsoft authentication...[/blue]")
            console.print("[yellow]Please complete the login in your browser[/yellow]")
            
            # Wait for callback with timeout
            timeout = 300  # 5 minutes timeout
            start_time = time.time()
            while not callback_data.get("code") and not callback_data.get("error"):
                if time.time() - start_time > timeout:
                    raise Exception("Authentication timed out")
                time.sleep(0.1)
            
            # Check for error
            if callback_data.get("error"):
                raise Exception(f"Authentication error: {callback_data.get('error')} - {callback_data.get('error_description')}")
            
            # Get the auth code from callback
            auth_code = callback_data["code"]
            console.print("[green]Authentication code received![/green]")
        
        # Complete the login process
        console.print("[blue]Completing Minecraft authentication...[/blue]")
        
        # Use the secure login data to complete the authentication
        login_data = minecraft_launcher_lib.microsoft_account.complete_login(
            client_id=CLIENT_ID,
            client_secret=None,  # No client secret for public clients
            redirect_uri=REDIRECT_URL,
            auth_code=auth_code,
            code_verifier=code_verifier  # Important for secure PKCE flow
        )
        
        # Log success and save data
        console.print("[green]Authentication successful![/green]")
        console.print(f"[blue]Logged in as: {login_data.get('name', 'Unknown')}[/blue]")
        
        # Save the refresh token for future use
        if "refresh_token" in login_data:
            config = load_config()
            config["refresh_token"] = login_data["refresh_token"]
            config["username"] = login_data["name"]
            save_config(config)
            console.print("[green]Saved refresh token for future use[/green]")
        
        return login_data
        
    except minecraft_launcher_lib.exceptions.AzureAppNotPermitted:
        console.print("[red]Your Azure application does not have permission to use the Minecraft API[/red]")
        console.print("[yellow]Make sure your application has been approved through the Microsoft form[/yellow]")
        raise Exception("Azure application not permitted")
    
    except minecraft_launcher_lib.exceptions.AccountNotOwnMinecraft:
        console.print("[red]This Microsoft account does not own Minecraft[/red]")
        raise Exception("Account does not own Minecraft")
    
    except Exception as e:
        console.print(f"[red]Authentication error: {str(e)}[/red]")
        raise Exception("Microsoft authentication failed")
```

## 3. Refresh Token Implementation

Add this function to use refresh tokens for subsequent logins:

```python
def refresh_microsoft_login():
    """Use refresh token to authenticate without browser login"""
    console.print("\n[blue]Attempting to use saved credentials...[/blue]")
    
    config = load_config()
    refresh_token = config.get("refresh_token")
    
    if not refresh_token:
        console.print("[yellow]No saved credentials found[/yellow]")
        return None
    
    try:
        console.print("[blue]Refreshing Microsoft authentication...[/blue]")
        
        # Complete refresh process
        login_data = minecraft_launcher_lib.microsoft_account.complete_refresh(
            client_id=CLIENT_ID,
            client_secret=None,  # No client secret for public clients
            redirect_uri=None,   # Not needed for refresh
            refresh_token=refresh_token
        )
        
        console.print("[green]Authentication refresh successful![/green]")
        console.print(f"[blue]Logged in as: {login_data.get('name', 'Unknown')}[/blue]")
        
        # Update the refresh token
        if "refresh_token" in login_data:
            config["refresh_token"] = login_data["refresh_token"]
            config["username"] = login_data["name"]
            save_config(config)
        
        return login_data
        
    except minecraft_launcher_lib.exceptions.InvalidRefreshToken:
        console.print("[yellow]Refresh token expired, need to log in again[/yellow]")
        # Clear the invalid refresh token
        config["refresh_token"] = None
        save_config(config)
        return None
        
    except Exception as e:
        console.print(f"[red]Refresh error: {str(e)}[/red]")
        return None
```

## 4. Update Join Server Function

Modify your `join_server` function to use these authentication methods:

```python
def join_server():
    """Handle server selection and joining with Microsoft authentication"""
    try:
        # Load servers and get user selection
        # ... (existing code) ...

        # Show authentication options
        console.print("\n[yellow]AUTHENTICATION OPTIONS:[/yellow]")
        console.print("1. [green]Try Microsoft authentication (for online servers)[/green]")
        console.print("2. [green]Use offline mode (some servers will reject this connection)[/green]")
        console.print("3. [green]Use official Minecraft launcher (requires official launcher installed)[/green]")
        
        auth_choice = Prompt.ask("Choose authentication method", choices=["1", "2", "3"], default="1")
        
        # Ensure version is installed regardless of choice
        console.print("\n[bold blue]Checking Minecraft version " + base_version + "...[/bold blue]")
        ensure_version_installed(base_version)
        
        if auth_choice == "1":
            # Try refresh first
            auth_data = refresh_microsoft_login()
            
            # If refresh failed, try full login
            if not auth_data:
                auth_data = microsoft_login()
                
            if auth_data:
                # Launch with Microsoft authentication
                launch_minecraft(version, server_address, auth_data)
            else:
                # Fall back to option selector if both failed
                console.print("[red]Microsoft authentication failed[/red]")
                if Confirm.ask("[yellow]Do you want to try offline mode instead?[/yellow]", default=True):
                    # Fall back to offline mode
                    # ... (existing offline mode code) ...
        
        # ... (continue with existing code for options 2 and 3) ...
        
    except Exception as e:
        console.print(f"\n[red]Error joining server: {str(e)}[/red]")
        return
```

## 5. Authentication Response Format

Upon successful authentication, `minecraft_launcher_lib.microsoft_account.complete_login()` returns:

```json
{
    "id": "UUID of the player",
    "name": "Minecraft username",
    "access_token": "Token for authentication",
    "refresh_token": "Token for future logins",
    "skins": [{ ... skin data ... }],
    "capes": [{ ... cape data ... }]
}
```

This data can be used directly with the `launch_minecraft()` function to authenticate with Minecraft servers.

## 6. Error Handling

Be prepared to handle these common exceptions:

1. `AzureAppNotPermitted`: Your app doesn't have permission for Minecraft API
2. `AccountNotOwnMinecraft`: User doesn't own Minecraft
3. `InvalidRefreshToken`: Refresh token expired, need new login

## 7. Security Considerations

1. Always use the secure PKCE flow with `get_secure_login_data()`
2. Never store access tokens persistently - only store refresh tokens
3. Use HTTPS for any external API calls
4. Validate state parameter to prevent CSRF attacks

## 8. Key Functions Reference

- `get_secure_login_data(client_id, redirect_uri, state=None)`: 
  Generates login URL, state, and PKCE code verifier

- `complete_login(client_id, client_secret, redirect_uri, auth_code, code_verifier=None)`:
  Completes the authentication process

- `complete_refresh(client_id, client_secret, redirect_uri, refresh_token)`:
  Refreshes authentication using a refresh token
