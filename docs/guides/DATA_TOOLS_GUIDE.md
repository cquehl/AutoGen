# 📊 Data Tools Guide

Your AutoGen CLI now has powerful database and file access capabilities!

## Quick Start

### 1. Configure Database Connection

Add to your `.env` file:

```bash
# SQLite (easiest to start with)
DATABASE_URL=sqlite:///./data/mydata.db

# Or PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/mydb

# Or MySQL
DATABASE_URL=mysql://user:password@localhost:3306/mydb
```

### 2. Launch Data Agent Team

```bash
./cli.py --team data
```

## What Can the Data Agent Do?

### 🗄️ Database Operations

**List all tables:**
```
You: What tables are in the database?
Data_Analyst: [Uses list_database_tables tool...]
```

**Describe table schema:**
```
You: Show me the schema for the users table
Data_Analyst: [Uses describe_database_table...]
```

**Query data:**
```
You: Show me all users over age 25
Data_Analyst: [Writes and executes: SELECT * FROM users WHERE age > 25 LIMIT 100]
```

**Insert data:**
```
You: Add a new user: name=Alice, age=30, email=alice@example.com
Data_Analyst: [Executes INSERT statement...]
```

**Complex analysis:**
```
You: What's the average age by department?
Data_Analyst: [Writes: SELECT department, AVG(age) FROM users GROUP BY department]
```

### 📁 File Operations

**Read files:**
```
You: Read the config file at /path/to/config.json
Data_Analyst: [Uses read_file tool...]
```

**List directory:**
```
You: What CSV files are in the data folder?
Data_Analyst: [Uses list_directory with pattern="*.csv"...]
```

**Read CSV:**
```
You: Parse the sales.csv file
Data_Analyst: [Uses read_csv tool, shows structured data...]
```

**Write results:**
```
You: Save these query results to output.csv
Data_Analyst: [Uses write_csv tool...]
```

## Example Workflows

### Workflow 1: Database Exploration

```bash
./cli.py --team data

You: I have a new database. Help me understand what's in it.

Data_Analyst: I'll explore your database.
[Lists all tables...]
Found 3 tables: users, orders, products

You: Describe the users table

Data_Analyst: Here's the schema for users:
- id: INTEGER (Primary Key)
- name: TEXT
- email: TEXT
- age: INTEGER
- created_at: TIMESTAMP

You: Show me the first 5 users

Data_Analyst: [Executes: SELECT * FROM users LIMIT 5]
[Shows results in formatted table...]
```

### Workflow 2: Data Analysis

```bash
./cli.py --team data

You: Analyze customer purchase patterns

Data_Analyst: I'll analyze the purchase data.
[Queries orders and products tables...]
[Joins tables, calculates metrics...]

Key insights:
- Average order value: $127.50
- Top product category: Electronics (42% of sales)
- Peak purchase time: 2-4 PM
- Repeat customer rate: 68%

You: Save this analysis to a report

Data_Analyst: [Writes detailed report to analysis_report.csv]
Saved to: /home/user/analysis_report.csv
```

### Workflow 3: CSV Data Processing

```bash
./cli.py --team data

You: I have a CSV file at ./data/sales_2024.csv. Analyze it.

Data_Analyst: [Reads CSV file...]
Loaded 1,247 rows with columns: date, product, amount, region

You: What's the total sales by region?

Data_Analyst: Analyzing sales by region:
- West: $542,890
- East: $489,230
- South: $367,120
- North: $298,450

You: Create a summary CSV with monthly totals

Data_Analyst: [Aggregates data by month, writes new CSV...]
Created: sales_monthly_summary.csv
```

## Using with Resume (-r) Flag

The data agent works great with memory:

```bash
# First session
./cli.py --team data
You: Analyze the users table and remember key insights
Data_Analyst: [Analyzes and saves insights to memory...]

# Next session (maybe next day)
./cli.py --team data -r
# Agent automatically loads previous insights!

You: Based on what we found yesterday, check if new users match the pattern
Data_Analyst: [Recalls previous analysis from memory, compares with new data...]
```

## Memory Commands with Data

```bash
You: /remember Our main database is the sales_db with 3 tables
✓ Saved to memory

You: /remember Important: always LIMIT queries to 1000 rows
✓ Saved to memory

You: /memories
[Shows all saved memories including database info...]

You: /search database
[Finds all memories related to "database"...]
```

## Advanced: Custom Queries

The agent can write queries for you OR you can specify them:

```bash
# Let agent write the query
You: Find all orders from the last 30 days

# Specify exact query
You: Run this query: SELECT product, SUM(amount) FROM sales WHERE date > '2024-01-01' GROUP BY product ORDER BY SUM(amount) DESC

# Let agent optimize your query
You: Is there a better way to write: SELECT * FROM huge_table WHERE value LIKE '%search%'
Data_Analyst: Yes! That query will be slow. Here's an optimized version...
```

## Tool Reference

### Database Tools

| Tool | Description |
|------|-------------|
| `query_database` | Execute any SQL query (SELECT, INSERT, UPDATE, DELETE) |
| `list_database_tables` | List all tables in the database |
| `describe_database_table` | Get schema for a specific table |

### File Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read text file contents |
| `read_csv` | Parse CSV file into structured data |
| `list_directory` | List files/directories with pattern matching |
| `write_file` | Write content to text file |
| `write_csv` | Write structured data to CSV |

## Safety Features

The Data Agent includes safety features:

- **Query validation** before execution
- **LIMIT clauses** automatically added to large queries
- **Read-only mode** by default (set in agent config)
- **File overwrite protection** (must explicitly set `overwrite=True`)
- **Error handling** with clear error messages

## Tips

1. **Always explore first**: Use `list_database_tables` before querying
2. **Check schemas**: Use `describe_database_table` to understand structure
3. **Limit results**: For large tables, always use LIMIT in queries
4. **Save important queries**: Use `/remember` to save useful query patterns
5. **Use resume flag**: Start with `-r` to load previous database context

## Troubleshooting

**"Database connection error"**
- Check DATABASE_URL in .env
- Ensure database server is running
- Verify credentials

**"Table not found"**
- Use `list_database_tables` to see available tables
- Check table name spelling

**"Permission denied" on file**
- Check file permissions
- Use absolute paths or paths relative to working directory

## Next Steps

1. Try the data team: `./cli.py --team data`
2. Connect your database in `.env`
3. Ask the agent to explore your data
4. Use `/remember` to save important findings
5. Use `-r` flag to resume with context

Happy analyzing! 🚀
