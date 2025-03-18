use clap::Parser;

/// CLI of the application
/// It can be run in either `setup`, `process`, `prove`, `verify` mode
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
pub(crate) struct Cli {
    // Setup mode
    #[arg(short, long)]
    pub setup: bool,

    // Process input mode
    #[arg(short, long)]
    pub process: bool,

    // Proving mode
    #[arg(short, long)]
    pub prove: bool,

    // Verification mode
    #[arg(short, long)]
    pub verify: bool,

    // File path
    #[arg(short, long)]
    pub file: String,
}
