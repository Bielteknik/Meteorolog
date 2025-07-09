from app.scheduler import JobScheduler

def main():
    """Projenin ana giriş noktası."""
    scheduler = JobScheduler()
    scheduler.run()

if __name__ == "__main__":
    main()