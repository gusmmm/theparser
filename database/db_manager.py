"""
MongoDB Database Manager for UQ (Unidade de Queimados) Database

This module provides functionality to:
- Connect to a local MongoDB database named 'UQ'
- Check connection health
- Disconnect from the database
- List database and collection information

Author: Agent
Date: 2025-10-10
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from icecream import ic
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Optional, Dict, List
from datetime import datetime
import sys

# Configure icecream for debugging
ic.configureOutput(prefix='[DB DEBUG] ')

# Rich console for beautiful output
console = Console()


class MongoDBManager:
    """
    MongoDB Manager for UQ database.
    
    Handles connection, health checks, and provides information about
    the database and its collections.
    """
    
    def __init__(self, host: str = "localhost", port: int = 27017, db_name: str = "UQ"):
        """
        Initialize MongoDB Manager.
        
        Args:
            host: MongoDB host address (default: localhost)
            port: MongoDB port (default: 27017)
            db_name: Database name (default: UQ)
        """
        self.host = host
        self.port = port
        self.db_name = db_name
        self.client: Optional[MongoClient] = None
        self.db = None
        self.is_connected = False
        
        ic(f"MongoDB Manager initialized for {host}:{port}/{db_name}")
    
    def connect(self) -> bool:
        """
        Connect to MongoDB database.
        Creates the database if it doesn't exist.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        console.print("\n[bold yellow]Connecting to MongoDB...[/bold yellow]")
        ic(f"Attempting connection to {self.host}:{self.port}")
        
        try:
            # Create MongoDB client with timeout
            self.client = MongoClient(
                host=self.host,
                port=self.port,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=5000
            )
            
            # Test connection by pinging the server
            self.client.admin.command('ping')
            
            # Connect to or create the UQ database
            self.db = self.client[self.db_name]
            self.is_connected = True
            
            ic("Connection successful")
            console.print(f"[bold green]✓ Connected to MongoDB:[/bold green] {self.host}:{self.port}")
            console.print(f"[bold green]✓ Database:[/bold green] {self.db_name}")
            
            # Check if database is new
            if self.db_name not in self.client.list_database_names():
                console.print(f"[bold cyan]ℹ Database '{self.db_name}' will be created on first document insert[/bold cyan]")
            
            return True
            
        except ConnectionFailure as e:
            ic(f"Connection failure: {e}")
            console.print(f"[bold red]✗ Connection failed:[/bold red] {e}")
            console.print("[yellow]Make sure MongoDB is running:[/yellow] sudo systemctl start mongod")
            self.is_connected = False
            return False
            
        except ServerSelectionTimeoutError as e:
            ic(f"Server selection timeout: {e}")
            console.print(f"[bold red]✗ Connection timeout:[/bold red] Could not connect to MongoDB")
            console.print(f"[yellow]Check if MongoDB is running on {self.host}:{self.port}[/yellow]")
            self.is_connected = False
            return False
            
        except Exception as e:
            ic(f"Unexpected error: {type(e).__name__}: {e}")
            console.print(f"[bold red]✗ Unexpected error:[/bold red] {e}")
            self.is_connected = False
            return False
    
    def check_health(self) -> Dict:
        """
        Check the health of the MongoDB connection and server.
        
        Returns:
            dict: Health status information
        """
        if not self.is_connected or self.client is None:
            console.print("[bold red]✗ Not connected to database[/bold red]")
            return {
                "connected": False,
                "error": "No active connection"
            }
        
        console.print("\n[bold yellow]Checking database health...[/bold yellow]")
        
        try:
            # Get server info
            server_info = self.client.server_info()
            
            # Get database stats
            db_stats = self.db.command("dbStats")
            
            # Get list of collections
            collections = self.db.list_collection_names()
            
            health_info = {
                "connected": True,
                "host": self.host,
                "port": self.port,
                "database": self.db_name,
                "mongodb_version": server_info.get("version", "unknown"),
                "collections_count": len(collections),
                "collections": collections,
                "database_size_mb": round(db_stats.get("dataSize", 0) / (1024 * 1024), 2),
                "storage_size_mb": round(db_stats.get("storageSize", 0) / (1024 * 1024), 2),
                "indexes_count": db_stats.get("indexes", 0),
                "objects_count": db_stats.get("objects", 0),
                "timestamp": datetime.now().isoformat()
            }
            
            ic("Health check successful")
            console.print("[bold green]✓ Database is healthy[/bold green]")
            
            return health_info
            
        except Exception as e:
            ic(f"Health check failed: {type(e).__name__}: {e}")
            console.print(f"[bold red]✗ Health check failed:[/bold red] {e}")
            return {
                "connected": False,
                "error": str(e)
            }
    
    def disconnect(self) -> bool:
        """
        Disconnect from MongoDB database.
        
        Returns:
            bool: True if disconnection successful
        """
        if not self.is_connected or self.client is None:
            console.print("[yellow]ℹ Already disconnected[/yellow]")
            return True
        
        console.print("\n[bold yellow]Disconnecting from MongoDB...[/bold yellow]")
        
        try:
            self.client.close()
            self.client = None
            self.db = None
            self.is_connected = False
            
            ic("Disconnected successfully")
            console.print("[bold green]✓ Disconnected from MongoDB[/bold green]")
            return True
            
        except Exception as e:
            ic(f"Disconnect error: {type(e).__name__}: {e}")
            console.print(f"[bold red]✗ Disconnect error:[/bold red] {e}")
            return False
    
    def list_database_info(self) -> None:
        """
        List comprehensive information about the database and its collections.
        Displays in a formatted table to the terminal.
        """
        if not self.is_connected or self.db is None:
            console.print("[bold red]✗ Not connected to database[/bold red]")
            return
        
        console.print("\n" + "="*80)
        
        # Get health info
        health = self.check_health()
        
        if not health.get("connected"):
            return
        
        # Create database info panel
        db_info = f"""[cyan]Host:[/cyan] {health['host']}:{health['port']}
[cyan]Database:[/cyan] {health['database']}
[cyan]MongoDB Version:[/cyan] {health['mongodb_version']}
[cyan]Collections:[/cyan] {health['collections_count']}
[cyan]Total Objects:[/cyan] {health['objects_count']}
[cyan]Data Size:[/cyan] {health['database_size_mb']} MB
[cyan]Storage Size:[/cyan] {health['storage_size_mb']} MB
[cyan]Indexes:[/cyan] {health['indexes_count']}
[cyan]Status:[/cyan] [bold green]Connected ✓[/bold green]
[cyan]Timestamp:[/cyan] {health['timestamp']}"""
        
        console.print(Panel(
            db_info,
            title=f"📊 Database: {self.db_name}",
            border_style="cyan"
        ))
        
        # If there are collections, show detailed info
        if health['collections']:
            console.print(f"\n[bold cyan]Collections in '{self.db_name}':[/bold cyan]\n")
            
            # Create table for collections
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Collection", style="cyan", width=30)
            table.add_column("Documents", justify="right", style="yellow")
            table.add_column("Avg Doc Size", justify="right", style="green")
            table.add_column("Total Size", justify="right", style="blue")
            table.add_column("Indexes", justify="right", style="magenta")
            
            try:
                for collection_name in sorted(health['collections']):
                    collection = self.db[collection_name]
                    stats = self.db.command("collStats", collection_name)
                    
                    doc_count = stats.get("count", 0)
                    avg_size = round(stats.get("avgObjSize", 0) / 1024, 2) if doc_count > 0 else 0
                    total_size = round(stats.get("size", 0) / 1024, 2)
                    index_count = stats.get("nindexes", 0)
                    
                    table.add_row(
                        collection_name,
                        str(doc_count),
                        f"{avg_size} KB",
                        f"{total_size} KB",
                        str(index_count)
                    )
                
                console.print(table)
                
            except Exception as e:
                ic(f"Error getting collection stats: {e}")
                console.print(f"[yellow]⚠ Could not retrieve detailed collection stats: {e}[/yellow]")
        else:
            console.print("\n[yellow]ℹ No collections found in database[/yellow]")
            console.print("[dim]Collections will be created when you insert documents[/dim]")
        
        console.print("\n" + "="*80)
    
    def create_collection(self, collection_name: str) -> bool:
        """
        Create a new collection in the database.
        
        Args:
            collection_name: Name of the collection to create
            
        Returns:
            bool: True if successful
        """
        if not self.is_connected or self.db is None:
            console.print("[bold red]✗ Not connected to database[/bold red]")
            return False
        
        try:
            if collection_name in self.db.list_collection_names():
                console.print(f"[yellow]ℹ Collection '{collection_name}' already exists[/yellow]")
                return True
            
            self.db.create_collection(collection_name)
            ic(f"Collection created: {collection_name}")
            console.print(f"[bold green]✓ Collection created:[/bold green] {collection_name}")
            return True
            
        except Exception as e:
            ic(f"Error creating collection: {e}")
            console.print(f"[bold red]✗ Error creating collection:[/bold red] {e}")
            return False
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_db_manager(host: str = "localhost", port: int = 27017, db_name: str = "UQ") -> MongoDBManager:
    """
    Create and return a MongoDB manager instance.
    
    Args:
        host: MongoDB host
        port: MongoDB port
        db_name: Database name
        
    Returns:
        MongoDBManager instance
    """
    return MongoDBManager(host=host, port=port, db_name=db_name)


# ============================================================================
# MAIN EXECUTION - Testing
# ============================================================================

if __name__ == "__main__":
    console.print("\n" + "="*80)
    console.print("[bold cyan]MongoDB Database Manager - UQ Database[/bold cyan]")
    console.print("="*80 + "\n")
    
    # Create manager instance
    db_manager = MongoDBManager()
    
    # Connect to database
    if not db_manager.connect():
        console.print("\n[bold red]Failed to connect to MongoDB![/bold red]")
        console.print("[yellow]Please ensure MongoDB is running:[/yellow]")
        console.print("  sudo systemctl start mongod")
        console.print("  sudo systemctl status mongod")
        sys.exit(1)
    
    # Check health
    health_info = db_manager.check_health()
    
    # List database information
    db_manager.list_database_info()
    
    # Example: Create a test collection (optional)
    # db_manager.create_collection("test_collection")
    
    # Disconnect
    db_manager.disconnect()
    
    console.print("\n[bold green]✓ Database operations completed successfully![/bold green]\n")
