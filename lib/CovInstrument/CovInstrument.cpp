#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Type.h"
#include "llvm/Pass.h"
#include "llvm/Support/AtomicOrdering.h"
#include "llvm/Support/raw_ostream.h"

using namespace llvm;

namespace {
  struct CovInstrument : public ModulePass {
    static char ID;
    CovInstrument() : ModulePass(ID) {}

    bool runOnModule(Module &M) override {
      LLVMContext &Context = M.getContext();
      IntegerType *Int64Ty = Type::getInt64Ty(Context);
      for (Function &F : M) {
        for (BasicBlock &BB : F) {
          IRBuilder<> Builder(&BB);
          Builder.SetInsertPoint(BB.getFirstInsertionPt());

          // Create a global counter for each basic block
          GlobalVariable *Counter = new GlobalVariable(M, Int64Ty, false, GlobalValue::ExternalLinkage, ConstantInt::get(Int64Ty, 0), "bb_counter");

          // Use atomic increment to update the counter
          LoadInst *LoadCounter = Builder.CreateLoad(Int64Ty, Counter);
          LoadCounter->setAtomic(AtomicOrdering::Monotonic);
          Value *IncCounter = Builder.CreateAdd(LoadCounter, ConstantInt::get(Int64Ty, 1));
          StoreInst *StoreCounter = Builder.CreateStore(IncCounter, Counter);
          StoreCounter->setAtomic(AtomicOrdering::Monotonic);
        }
      }
      return true;
    }
  };
}

char CovInstrument::ID = 0;
static RegisterPass<CovInstrument> X("thread-safe-coverage", "Thread-Safe Coverage Instrumentation Pass", false, false);
