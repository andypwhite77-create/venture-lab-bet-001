"use strict";
const { PublicKey, Transaction, TransactionMessage, VersionedTransaction } = require('@solana/web3.js');
const { AccountLayout, TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID,
  createCloseAccountInstruction } = require('@solana/spl-token');
const { Solana } = require('../solana');

const PROGRAMS = [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID];
const sameKey = (a,b) => new PublicKey(a).equals(new PublicKey(b));

async function closeTokenAccountSolana(fastify, body) {
  const { network, address, tokenAccount, expectedMint, simulateOnly=true } = body || {};
  if (!network || !address || !tokenAccount || !expectedMint)
    throw fastify.httpErrors.badRequest('network, address, tokenAccount and expectedMint are required');
  const solana = await Solana.getInstance(network);
  const wallet = new PublicKey(address); const account = new PublicKey(tokenAccount);
  const info = await solana.connection.getAccountInfo(account, 'confirmed');
  if (!info) throw fastify.httpErrors.badRequest('token_account_not_found');
  const program = PROGRAMS.find(p => p.equals(info.owner));
  if (!program) throw fastify.httpErrors.badRequest('unsupported_token_program');
  if (info.data.length < AccountLayout.span) throw fastify.httpErrors.badRequest('malformed_token_account');
  const decoded = AccountLayout.decode(info.data.subarray(0, AccountLayout.span));
  const owner = new PublicKey(decoded.owner); const mint = new PublicKey(decoded.mint);
  if (!owner.equals(wallet)) throw fastify.httpErrors.badRequest('wallet_not_token_owner');
  if (!sameKey(mint, expectedMint)) throw fastify.httpErrors.badRequest('mint_mismatch');
  if (BigInt(decoded.amount.toString()) !== 0n) throw fastify.httpErrors.badRequest('token_balance_nonzero');
  const ix = createCloseAccountInstruction(account, wallet, wallet, [], program);
  const { blockhash } = await solana.connection.getLatestBlockhash('confirmed');
  const message = new TransactionMessage({ payerKey:wallet, recentBlockhash:blockhash, instructions:[ix] }).compileToV0Message();
  const tx = new VersionedTransaction(message); const signer = await solana.getWallet(address); tx.sign([signer]);
  const sim = await solana.connection.simulateTransaction(tx, { sigVerify:true });
  if (sim.value.err) throw fastify.httpErrors.badRequest('close_simulation_failed');
  if (simulateOnly !== false)
    return { simulated:true, tokenAccount, mint:mint.toBase58(), program:program.toBase58(), reclaimableLamports:info.lamports };
  const { confirmed, signature, txData } = await solana.sendAndConfirmRawTransaction(tx);
  if (!confirmed || !txData) throw fastify.httpErrors.internalServerError('close_confirmation_failed');
  const feeSol = txData.meta?.fee ? txData.meta.fee / 1_000_000_000 : 0;
  return { simulated:false, signature, tokenAccount, mint:mint.toBase58(), program:program.toBase58(), reclaimedLamports:info.lamports, feeSol };
}
module.exports = { closeTokenAccountSolana };
