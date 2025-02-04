GreweFeatures = {
  'comp': 254,
  'rational': 61,
  'mem': 107,
  'localmem': 104,
  'coalesced': 100,
  'atomic': 20,
  'F2:coalesced/mem': 1,
  'F4:comp/mem': 1,
}

InstCountFeatures = {
  'TotalInsts' : 523,
  'TotalBlocks' : 52,
  'TotalFuncs' : 66,
  'Ret' : 4,
  'Br' : 1,
  'Switch' : 1,
  'IndirectBr' : 1,
  'Invoke' : 1, # That is indeed 1.
  'Resume' : 1,
  'Unreachable' : 1,
  'CleanupRet' : 1,
  'CatchRet' : 1,
  'CatchSwitch' : 14,
  'CallBr' : 117,
  'FNeg' : 89,
  'Add' : 55,
  'FAdd' : 55,
  'Sub' : 56,
  'FSub' : 91,
  'Mul' : 8,
  'FMul' : 55,
  'UDiv' : 64,
  'SDiv' : 11,
  'FDiv' : 8,
  'URem' : 1,
  'SRem' : 36,
  'FRem' : 21,
  'Shl' : 28,
  'LShr' : 35,
  'AShr' : 61,
  'And' : 76,
  'Or' : 42,
  'Xor' : 90,
  'Alloca' : 84,
  'Load' : 112,
  'Store' : 1,
  'GetElementPtr' : 1,
  'Fence' : 1,
  'AtomicCmpXchg' : 30,
  'AtomicRMW' : 96,
  'Trunc' : 52,
  'ZExt' : 8,
  'SExt' : 30,
  'FPToUI' : 27,
  'FPToSI' : 17,
  'UIToFP' : 64,
  'SIToFP' : 64,
  'FPTrunc' : 28,
  'FPExt' : 13,
  'PtrToInt' : 66,
  'IntToPtr' : 43,
  'BitCast' : 1,
  'AddrSpaceCast' : 1,
  'CleanupPad' : 42,
  'CatchPad' : 21,
  'ICmp' : 111,
  'FCmp' : 129,
  'PHI' : 39,
  'Call' : 1,
  'Select' : 1,
  'UserOp1' : 1,
  'UserOp2' : 60,
  'VAArg' : 44,
  'ExtractElement' : 47,
  'InsertElement' : 26,
  'ShuffleVector' : 1,
  'ExtractValue' : 0,
  'InsertValue' : 1,
  'LandingPad' : 1,
  'Freeze' : 1,
}

AutophaseFeatures = {
  'BBNumArgsHi' : 25,
  'BBNumArgsLo' : 19,
  'onePred' : 34,
  'onePredOneSuc' : 32,
  'onePredTwoSuc' : 26,
  'oneSuccessor' : 32,
  'twoPred' : 31,
  'twoPredOneSuc' : 17,
  'twoEach' : 31,
  'twoSuccessor' : 34,
  'morePreds' : 9,
  'BB03Phi' : 21,
  'BBHiPhi' : 25,
  'BBNoPhi' : 43,
  'BeginPhi' : 32,
  'BranchCount' : 50,
  'returnInt' : 44,
  'CriticalCount' : 57,
  'NumEdges' : 84,
  'const32Bit' : 135,
  'const64Bit' : 262,
  'numConstZeroes' : 119,
  'numConstOnes' : 65,
  'UncondBranches' : 32,
  'binaryConstArg' : 97,
  'AShr' : 28,
  'Add' : 117,
  'Alloca' : 42,
  'And' : 35,
  'BlockMid' : 11,
  'BlockLow' : 51,
  'BitCast' : 66,
  'Br' : 50,
  'Call' : 129,
  'GetElementPtr' : 112,
  'ICmp' : 42,
  'LShr' : 21,
  'Load' : 90,
  'Mul' : 56,
  'Or' : 61,
  'PHI' : 111,
  'Ret' : 11,
  'SExt' : 52,
  'Select' : 39,
  'Shl' : 36,
  'Store' : 84,
  'Sub' : 55,
  'Trunc' : 30,
  'Xor' : 76,
  'ZExt' : 96,
  'TotalBlocks' : 51,
  'TotalInsts' : 523,
  'TotalMemInst' : 269,
  'TotalFuncs' : 11,
  'ArgsPhi' : 230,
  'testUnary' : 229,
}

normalizer = {
  'GreweFeatures'     : GreweFeatures,
  'InstCountFeatures' : InstCountFeatures,
  'AutophaseFeatures' : AutophaseFeatures,
}
