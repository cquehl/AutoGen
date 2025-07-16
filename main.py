# main.py
import asyncio
import weather_orchestrator

async def main():
    print("Main ---- Starting")
    # The orchestrator now handles its own configuration
    await weather_orchestrator.run()

if __name__ == "__main__":
    asyncio.run(main())