use anchor_lang::prelude::*;
use anchor_spl::token::{self, Mint, Token, TokenAccount, Transfer};

declare_id!("Fg6PaFpoGXkYsidMpWTK6W2BeZ7FEfcYkg476zPFsLnS");

#[program]
pub mod ai_agent_escrow {
    use super::*;

    /// 初始化託管帳戶
    /// 買方將資金鎖定，等待賣方交付服務
    pub fn initialize_escrow(
        ctx: Context<InitializeEscrow>,
        order_id: String,
        amount: u64,
    ) -> Result<()> {
        let escrow = &mut ctx.accounts.escrow;
        escrow.buyer = ctx.accounts.buyer.key();
        escrow.seller = ctx.accounts.seller.key();
        escrow.amount = amount;
        escrow.order_id = order_id;
        escrow.status = EscrowStatus::Locked as u8;
        
        // 從買方轉帳到託管帳戶
        let transfer_ctx = ctx.accounts.clone();
        token::transfer(
            CpiContext::new(transfer_ctx.token_program.clone(), transfer_ctx.clone()),
            amount,
        )?;
        
        Ok(())
    }

    /// 賣方確認交付，買方確認後放款
    pub fn confirm_delivery(ctx: Context<ConfirmDelivery>) -> Result<()> {
        let escrow = &mut ctx.accounts.escrow;
        require!(escrow.status == EscrowStatus::Locked as u8, EscrowError::InvalidStatus);
        
        escrow.status = EscrowStatus::Completed as u8;
        
        // 將資金從託管轉給賣方
        let transfer_ctx = ctx.accounts.clone();
        token::transfer(
            CpiContext::new(transfer_ctx.token_program.clone(), transfer_ctx.clone()),
            escrow.amount,
        )?;
        
        Ok(())
    }

    /// 取消訂單並退款給買方
    pub fn cancel_escrow(ctx: Context<CancelEscrow>) -> Result<()> {
        let escrow = &mut ctx.accounts.escrow;
        require!(escrow.status == EscrowStatus::Locked as u8, EscrowError::InvalidStatus);
        
        escrow.status = EscrowStatus::Cancelled as u8;
        
        // 將資金退回買方
        let transfer_ctx = ctx.accounts.clone();
        token::transfer(
            CpiContext::new(transfer_ctx.token_program.clone(), transfer_ctx.clone()),
            escrow.amount,
        )?;
        
        Ok(())
    }
}

#[derive(Accounts)]
pub struct InitializeEscrow<'info> {
    #[account(mut)]
    pub buyer: Signer<'info>,
    pub seller: AccountInfo<'info>,
    #[account(mut)]
    pub buyer_token_account: Account<'info, TokenAccount>,
    #[account(mut)]
    pub escrow_token_account: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
    pub escrow: Account<'info, Escrow>,
}

#[derive(Accounts)]
pub struct ConfirmDelivery<'info> {
    #[account(mut)]
    pub buyer: Signer<'info>,
    #[account(mut)]
    pub seller: Signer<'info>,
    #[account(mut)]
    pub escrow_token_account: Account<'info, TokenAccount>,
    #[account(mut)]
    pub seller_token_account: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
    #[account(mut)]
    pub escrow: Account<'info, Escrow>,
}

#[derive(Accounts)]
pub struct CancelEscrow<'info> {
    #[account(mut)]
    pub buyer: Signer<'info>,
    #[account(mut)]
    pub escrow_token_account: Account<'info, TokenAccount>,
    #[account(mut)]
    pub buyer_token_account: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
    #[account(mut)]
    pub escrow: Account<'info, Escrow>,
}

#[account]
pub struct Escrow {
    pub buyer: Pubkey,
    pub seller: Pubkey,
    pub amount: u64,
    pub order_id: String,
    pub status: u8,
}

#[error_code]
pub enum EscrowError {
    #[msg("Invalid escrow status")]
    InvalidStatus,
}

#[repr(u8)]
pub enum EscrowStatus {
    Locked,
    Completed,
    Cancelled,
}
