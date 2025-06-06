# cli.py
#!/usr/bin/env python3
import click
import asyncio
import json
import sys
import os
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database import SessionLocal
from app.models.database import Device, Notification, Script
from app.pulseway.client import PulsewayClient
from app.services.data_sync import DataSyncService

console = Console()

def get_db():
    """Get database session"""
    return SessionLocal()

def get_pulseway_client():
    """Get Pulseway client from environment variables"""
    token_id = os.getenv("PULSEWAY_TOKEN_ID")
    token_secret = os.getenv("PULSEWAY_TOKEN_SECRET")
    base_url = os.getenv("PULSEWAY_BASE_URL", "https://api.pulseway.com/v3/")
    
    if not token_id or not token_secret:
        console.print("[red]Error: PULSEWAY_TOKEN_ID and PULSEWAY_TOKEN_SECRET environment variables are required[/red]")
        sys.exit(1)
    
    return PulsewayClient(base_url, token_id, token_secret)

@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Pulseway CLI - Command line interface for Pulseway backend operations"""

# Device commands
@cli.group()
def devices():
    """Device management commands"""

@devices.command()
@click.option('--organization', '-o', help='Filter by organization')
@click.option('--site', '-s', help='Filter by site')
@click.option('--group', '-g', help='Filter by group')
@click.option('--online-only', is_flag=True, help='Show only online devices')
@click.option('--offline-only', is_flag=True, help='Show only offline devices')
@click.option('--alerts-only', is_flag=True, help='Show only devices with alerts')
@click.option('--limit', '-l', default=50, help='Maximum number of devices to show')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format')
def list(organization, site, group, online_only, offline_only, alerts_only, limit, output_format):
    """List devices with optional filtering"""
    
    db = get_db()
    
    query = db.query(Device)
    
    # Apply filters
    if organization:
        query = query.filter(Device.organization_name.ilike(f"%{organization}%"))
    if site:
        query = query.filter(Device.site_name.ilike(f"%{site}%"))
    if group:
        query = query.filter(Device.group_name.ilike(f"%{group}%"))
    if online_only:
        query = query.filter(Device.is_online == True)
    if offline_only:
        query = query.filter(Device.is_online == False)
    if alerts_only:
        query = query.filter((Device.critical_notifications > 0) | (Device.elevated_notifications > 0))
    
    devices = query.limit(limit).all()
    
    if output_format == 'json':
        device_list = []
        for device in devices:
            device_list.append({
                'identifier': device.identifier,
                'name': device.name,
                'organization': device.organization_name,
                'site': device.site_name,
                'group': device.group_name,
                'is_online': device.is_online,
                'critical_alerts': device.critical_notifications,
                'elevated_alerts': device.elevated_notifications
            })
        click.echo(json.dumps(device_list, indent=2))
        
    elif output_format == 'csv':
        click.echo("Name,Organization,Site,Group,Online,Critical,Elevated")
        for device in devices:
            click.echo(f"{device.name},{device.organization_name},{device.site_name},{device.group_name},{device.is_online},{device.critical_notifications},{device.elevated_notifications}")
    
    else:  # table format
        table = Table(title="Pulseway Devices")
        table.add_column("Name", style="cyan")
        table.add_column("Organization", style="blue")
        table.add_column("Site", style="blue")
        table.add_column("Group", style="blue")
        table.add_column("Status", style="green")
        table.add_column("Critical", style="red")
        table.add_column("Elevated", style="yellow")
        
        for device in devices:
            status = "🟢 Online" if device.is_online else "🔴 Offline"
            critical = str(device.critical_notifications or 0)
            elevated = str(device.elevated_notifications or 0)
            
            table.add_row(
                device.name or "Unknown",
                device.organization_name or "Unknown",
                device.site_name or "Unknown", 
                device.group_name or "Unknown",
                status,
                critical,
                elevated
            )
        
        console.print(table)
    
    db.close()

@devices.command()
@click.argument('device_id')
def info(device_id):
    """Get detailed information about a specific device"""
    
    db = get_db()
    device = db.query(Device).filter(Device.identifier == device_id).first()
    
    if not device:
        console.print(f"[red]Device {device_id} not found[/red]")
        sys.exit(1)
    
    # Create info panel
    info_text = f"""
[bold]Device Information[/bold]

[cyan]Basic Info:[/cyan]
  Name: {device.name}
  Identifier: {device.identifier}
  Description: {device.description or 'N/A'}
  Type: {device.computer_type or 'Unknown'}

[cyan]Status:[/cyan]
  Online: {'🟢 Yes' if device.is_online else '🔴 No'}
  Agent Installed: {'✓' if device.is_agent_installed else '✗'}
  In Maintenance: {'✓' if device.in_maintenance else '✗'}
  Last Seen: {device.last_seen_online or 'Unknown'}

[cyan]Location:[/cyan]
  Organization: {device.organization_name or 'Unknown'}
  Site: {device.site_name or 'Unknown'}
  Group: {device.group_name or 'Unknown'}

[cyan]Performance:[/cyan]
  CPU Usage: {device.cpu_usage}%
  Memory Usage: {device.memory_usage}%
  Uptime: {device.uptime or 'Unknown'}

[cyan]Security:[/cyan]
  Antivirus: {device.antivirus_enabled or 'Unknown'}
  Firewall: {'Enabled' if device.firewall_enabled else 'Disabled' if device.firewall_enabled is False else 'Unknown'}
  UAC: {'Enabled' if device.uac_enabled else 'Disabled' if device.uac_enabled is False else 'Unknown'}

[cyan]Alerts:[/cyan]
  Critical: {device.critical_notifications or 0}
  Elevated: {device.elevated_notifications or 0}
  Normal: {device.normal_notifications or 0}
  Low: {device.low_notifications or 0}
"""
    
    console.print(Panel(info_text, title=f"Device: {device.name}", border_style="blue"))
    db.close()

@devices.command()
def stats():
    """Show device statistics"""
    
    db = get_db()
    
    total = db.query(Device).count()
    online = db.query(Device).filter(Device.is_online == True).count()
    offline = total - online
    with_agent = db.query(Device).filter(Device.is_agent_installed == True).count()
    critical_alerts = db.query(Device).filter(Device.critical_notifications > 0).count()
    elevated_alerts = db.query(Device).filter(Device.elevated_notifications > 0).count()
    
    stats_text = f"""
[bold]Device Statistics[/bold]

[cyan]Device Counts:[/cyan]
  Total Devices: {total}
  Online: {online}
  Offline: {offline}
  With Agent: {with_agent}

[cyan]Alerts:[/cyan]
  Devices with Critical Alerts: {critical_alerts}
  Devices with Elevated Alerts: {elevated_alerts}

[cyan]Health:[/cyan]
  Online Percentage: {(online/total*100):.1f}%
  Agent Coverage: {(with_agent/total*100):.1f}%
"""
    
    console.print(Panel(stats_text, title="System Overview", border_style="green"))
    db.close()

# Script commands
@cli.group()
def scripts():
    """Script management commands"""

@scripts.command()
@click.option('--platform', help='Filter by platform (Windows, Linux, Mac OS)')
@click.option('--category', help='Filter by category')
@click.option('--search', help='Search in script name or description')
@click.option('--limit', '-l', default=20, help='Maximum number of scripts to show')
def list(platform, category, search, limit):
    """List available scripts"""
    
    db = get_db()
    query = db.query(Script)
    
    if platform:
        query = query.filter(Script.platforms.contains([platform]))
    if category:
        query = query.filter(Script.category_name.ilike(f"%{category}%"))
    if search:
        query = query.filter(
            (Script.name.ilike(f"%{search}%")) | 
            (Script.description.ilike(f"%{search}%"))
        )
    
    scripts = query.limit(limit).all()
    
    table = Table(title="Available Scripts")
    table.add_column("Name", style="cyan")
    table.add_column("Category", style="blue")
    table.add_column("Platforms", style="green")
    table.add_column("Built-in", style="yellow")
    table.add_column("Created By", style="magenta")
    
    for script in scripts:
        platforms = ", ".join(script.platforms) if script.platforms else "Unknown"
        built_in = "✓" if script.is_built_in else "✗"
        
        table.add_row(
            script.name,
            script.category_name or "Uncategorized",
            platforms,
            built_in,
            script.created_by or "Unknown"
        )
    
    console.print(table)
    db.close()

@scripts.command()
@click.argument('script_id')
@click.argument('device_id')
@click.option('--variables', help='JSON string of script variables')
def execute(script_id, device_id, variables):
    """Execute a script on a device"""
    
    db = get_db()
    
    # Check if device exists and is online
    device = db.query(Device).filter(Device.identifier == device_id).first()
    if not device:
        console.print(f"[red]Device {device_id} not found[/red]")
        sys.exit(1)
    
    if not device.is_online:
        console.print(f"[red]Device {device.name} is offline[/red]")
        sys.exit(1)
    
    # Check if script exists
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        console.print(f"[red]Script {script_id} not found[/red]")
        sys.exit(1)
    
    client = get_pulseway_client()
    
    # Parse variables if provided
    script_variables = None
    if variables:
        try:
            script_variables = json.loads(variables)
        except json.JSONDecodeError:
            console.print("[red]Invalid JSON format for variables[/red]")
            sys.exit(1)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Executing script {script.name} on {device.name}...", total=None)
        
        try:
            response = client.run_script(script_id, device_id, script_variables)
            execution_data = response.get('Data', {})
            execution_id = execution_data.get('ExecutionId')
            
            if execution_id:
                console.print(f"[green]✓ Script execution started successfully[/green]")
                console.print(f"Execution ID: {execution_id}")
            else:
                console.print("[red]✗ Failed to start script execution[/red]")
                
        except Exception as e:
            console.print(f"[red]✗ Script execution failed: {str(e)}[/red]")
    
    db.close()

# Monitoring commands
@cli.group()
def monitoring():
    """Monitoring and alerting commands"""

@monitoring.command()
def dashboard():
    """Show monitoring dashboard"""
    
    db = get_db()
    
    # Get basic stats
    total_devices = db.query(Device).count()
    online_devices = db.query(Device).filter(Device.is_online == True).count()
    offline_devices = total_devices - online_devices
    
    # Get alert counts
    critical_devices = db.query(Device).filter(Device.critical_notifications > 0).count()
    elevated_devices = db.query(Device).filter(Device.elevated_notifications > 0).count()
    
    # Get recent notifications
    recent_notifications = db.query(Notification).order_by(
        Notification.datetime.desc()
    ).limit(5).all()
    
    # Create dashboard
    dashboard_text = f"""
[bold]Pulseway Monitoring Dashboard[/bold]

[cyan]System Status:[/cyan]
  🟢 Online Devices: {online_devices}
  🔴 Offline Devices: {offline_devices}
  ⚠️  Critical Alerts: {critical_devices}
  ⚠️  Elevated Alerts: {elevated_devices}
  
[cyan]Health Score:[/cyan]
  Online: {(online_devices/total_devices*100):.1f}%
  Critical Issues: {(critical_devices/total_devices*100):.1f}%
"""
    
    console.print(Panel(dashboard_text, title="System Dashboard", border_style="blue"))
    
    # Show recent notifications
    if recent_notifications:
        table = Table(title="Recent Notifications")
        table.add_column("Time", style="dim")
        table.add_column("Priority", style="bold")
        table.add_column("Message", style="white")
        
        for notif in recent_notifications:
            priority_color = {
                'critical': 'red',
                'elevated': 'yellow', 
                'normal': 'blue',
                'low': 'green'
            }.get(notif.priority.lower(), 'white')
            
            time_str = notif.datetime.strftime("%H:%M:%S") if notif.datetime else "Unknown"
            
            table.add_row(
                time_str,
                Text(notif.priority.upper(), style=priority_color),
                notif.message[:80] + "..." if len(notif.message) > 80 else notif.message
            )
        
        console.print(table)
    
    db.close()

@monitoring.command()
@click.option('--priority', type=click.Choice(['critical', 'elevated', 'normal', 'low']), help='Filter by priority')
@click.option('--limit', '-l', default=20, help='Maximum number of notifications to show')
def alerts(priority, limit):
    """Show recent alerts and notifications"""
    
    db = get_db()
    query = db.query(Notification)
    
    if priority:
        query = query.filter(Notification.priority.ilike(priority))
    
    notifications = query.order_by(Notification.datetime.desc()).limit(limit).all()
    
    table = Table(title="System Alerts")
    table.add_column("Time", style="dim")
    table.add_column("Priority", style="bold") 
    table.add_column("Device", style="cyan")
    table.add_column("Message", style="white")
    
    for notif in notifications:
        priority_color = {
            'critical': 'red',
            'elevated': 'yellow',
            'normal': 'blue', 
            'low': 'green'
        }.get(notif.priority.lower(), 'white')
        
        time_str = notif.datetime.strftime("%Y-%m-%d %H:%M:%S") if notif.datetime else "Unknown"
        device_name = "Unknown"
        
        if notif.device:
            device_name = notif.device.name
        
        table.add_row(
            time_str,
            Text(notif.priority.upper(), style=priority_color),
            device_name,
            notif.message[:60] + "..." if len(notif.message) > 60 else notif.message
        )
    
    console.print(table)
    db.close()

# Sync commands
@cli.group()
def sync():
    """Data synchronization commands"""

@sync.command()
def now():
    """Trigger immediate data synchronization"""
    
    client = get_pulseway_client()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        task = progress.add_task("Synchronizing data from Pulseway...", total=None)
        
        try:
            sync_service = DataSyncService(client)
            asyncio.run(sync_service.sync_all_data())
            console.print("[green]✓ Data synchronization completed successfully[/green]")
            
        except Exception as e:
            console.print(f"[red]✗ Data synchronization failed: {str(e)}[/red]")
            sys.exit(1)

@sync.command()
def status():
    """Show synchronization status"""
    
    db = get_db()
    
    # Get last update times
    last_device_update = db.query(Device.updated_at).order_by(Device.updated_at.desc()).first()
    last_notification_update = db.query(Notification.created_at).order_by(Notification.created_at.desc()).first()
    
    device_count = db.query(Device).count()
    notification_count = db.query(Notification).count()
    script_count = db.query(Script).count()
    
    status_text = f"""
[bold]Synchronization Status[/bold]

[cyan]Data Counts:[/cyan]
  Devices: {device_count}
  Notifications: {notification_count}
  Scripts: {script_count}

[cyan]Last Updates:[/cyan]
  Devices: {last_device_update[0] if last_device_update else 'Never'}
  Notifications: {last_notification_update[0] if last_notification_update else 'Never'}
"""
    
    console.print(Panel(status_text, title="Sync Status", border_style="blue"))
    db.close()

# Main entry point
if __name__ == '__main__':
    cli()