#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Type.h"
#include "llvm/Pass.h"
#include "llvm/Support/AtomicOrdering.h"
#include "llvm/Support/raw_ostream.h"
#include <llvm/IR/DebugInfoMetadata.h>


using namespace llvm;

namespace
{
  struct CovInstrument : public ModulePass
  {
    static char ID;
    CovInstrument() : ModulePass(ID) {}

    bool runOnModule(Module &M) override
    {
      LLVMContext &Context = M.getContext();
      IntegerType *Int64Ty = Type::getInt64Ty(Context);
      std::map<std::string, std::vector<Function *>> fileFunctionMap;

      for (Function &F : M)
      {
        if (F.isDeclaration())
        {
          continue;
        }

        // Create a global array for each function
        unsigned int NumBBs = std::distance(F.begin(), F.end());
        ArrayType *ArrayTy = ArrayType::get(Int64Ty, NumBBs);
        GlobalVariable *BBCounters = new GlobalVariable(M, ArrayTy, false, GlobalValue::InternalLinkage, Constant::getNullValue(ArrayTy), F.getName() + "_counters");

        // Insert atomic increment operations in each basic block
        insertAtomicIncrements(F, BBCounters, Int64Ty);

        // Group functions by file name
        if (DISubprogram *SP = F.getSubprogram())
        {
          std::string FileName = SP->getFile()->getFilename().str();
          fileFunctionMap[FileName].push_back(&F);
        }
      }

      // Insert calls to bc_cov_set_file and bc_cov
      insertbcCovCalls(M, fileFunctionMap, Int64Ty);

      return true;
    }

    void insertAtomicIncrements(Function &F, GlobalVariable *BBCounters, IntegerType *Int64Ty)
    {
      unsigned int BBIndex = 0;
      for (BasicBlock &BB : F)
      {
        IRBuilder<> Builder(&BB);

        // Create an atomic increment for the corresponding counter
        std::vector<Value *> Indices{ConstantInt::get(Int64Ty, 0), ConstantInt::get(Int64Ty, BBIndex++)};
        Value *Ptr = Builder.CreateInBoundsGEP(BBCounters, Indices);
        LoadInst *LoadedVal = Builder.CreateLoad(Int64Ty, Ptr);
        LoadedVal->setAtomic(AtomicOrdering::Monotonic);
        Value *IncVal = Builder.CreateAdd(LoadedVal, ConstantInt::get(Int64Ty, 1));
        StoreInst *Store = Builder.CreateStore(IncVal, Ptr);
        Store->setAtomic(AtomicOrdering::Monotonic);
      }
    }

    void insertbcCovCalls(Module &M, std::map<std::string, std::vector<Function *>> &fileFunctionMap, IntegerType *Int64Ty)
    {
      LLVMContext &Context = M.getContext();
      // create a new function named _bc_cov_dump 
      FunctionType *DumpFuncType = FunctionType::get(Type::getVoidTy(Context), false);
      Function *DumpFunc = Function::Create(DumpFuncType, GlobalValue::ExternalLinkage, "bc_cov_dump", &M);


      BasicBlock *BB = BasicBlock::Create(Context, "entry", DumpFunc);
      IRBuilder<> builder(BB);

      for (auto &fileFuncPair : fileFunctionMap)
      {
        const std::string &fileName = fileFuncPair.first;
        std::vector<Function *> &functions = fileFuncPair.second;
        int numFuncs = functions.size();

        // Insert call to bc_cov_set_file
        insertSetFileCall(M, fileName, numFuncs, builder);

        for (Function *F : functions)
        {
          // Get the global counters array for the function
          GlobalVariable *BBCounters = M.getGlobalVariable((F->getName() + "_counters").str());
          unsigned int NumBBs = std::distance(F->begin(), F->end());

          // Insert call to bc_cov
          insertCovCall(M, *F, BBCounters, NumBBs, Int64Ty, builder);
        }
      }
    }

    void insertSetFileCall(Module &M, const std::string &fileName, int numFuncs, IRBuilder<> &Builder)
    {
      LLVMContext &Context = M.getContext();
      FunctionType *SetFileType = FunctionType::get(Type::getVoidTy(Context), {Type::getInt8PtrTy(Context), Type::getInt32Ty(Context), Type::getInt32Ty(Context)}, false);
      FunctionCallee SetFileFunc = M.getOrInsertFunction("bc_cov_set_file", SetFileType);

      // Create arguments for the call
      Constant *FileNameStr = Builder.CreateGlobalStringPtr(fileName);
      Value *FileNameLen = Builder.getInt32(fileName.length());
      Value *NumFuncsVal = Builder.getInt32(numFuncs);

      Builder.CreateCall(SetFileFunc, {FileNameStr, FileNameLen, NumFuncsVal});
    }

    void insertCovCall(Module &M, Function &F, GlobalVariable *BBCounters, unsigned int NumBBs, IntegerType *Int64Ty, IRBuilder<> &Builder)
    {
      LLVMContext &Context = M.getContext();
      FunctionType *CovFuncType = FunctionType::get(Type::getVoidTy(Context), {Type::getInt8PtrTy(Context), Type::getInt32Ty(Context), Int64Ty->getPointerTo(), Type::getInt32Ty(Context)}, false);
      FunctionCallee CovFunc = F.getParent()->getOrInsertFunction("bc_cov", CovFuncType);

      // Create arguments for the call
      Constant *FuncNameStr = Builder.CreateGlobalStringPtr(F.getName());
      Value *FuncNameLen = Builder.getInt32(F.getName().size());
      Value *BBCountersPtr = Builder.CreatePointerCast(BBCounters, Int64Ty->getPointerTo());
      Value *NumBBsVal = Builder.getInt32(NumBBs);

      // Insert call at the end of the function
      for (auto &BB : F)
      {
        if (isa<ReturnInst>(BB.getTerminator()))
        {
          Builder.SetInsertPoint(BB.getTerminator());
          Builder.CreateCall(CovFunc, {FuncNameStr, FuncNameLen, BBCountersPtr, NumBBsVal});
        }
      }
    }
  };
} // namespace

  char CovInstrument::ID = 0;
  static RegisterPass<CovInstrument> X("cov-instrument", "Thread-Safe Coverage Instrumentation Pass", false, false);
