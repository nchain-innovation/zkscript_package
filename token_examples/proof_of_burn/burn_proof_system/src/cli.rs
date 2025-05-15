use clap::{Parser, Subcommand};

/// CLI of the application
/// It can be run in either `setup`, `prove`, or `verify` mode
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
pub(crate) struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand, Debug)]
pub(crate) enum Commands {
    /// Setup mode
    Setup,
    /// Verification mode
    Verify,
    /// Proving mode
    Prove
}
