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
#include <llvm/Support/Debug.h>
#include <llvm/Support/CommandLine.h>

#include <set>
#include <map>
#include <fstream>

#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"

using namespace llvm;

// Create an option to pass the output file name
static cl::opt<std::string> OutputFilename("output", cl::desc("Specify output filename"), cl::value_desc("filename"));

namespace
{
  struct CovInstrument : public ModulePass
  {
    static char ID;
    rapidjson::StringBuffer s; 
    rapidjson::Writer<rapidjson::StringBuffer> writer;

    CovInstrument() : ModulePass(ID) {}

    bool runOnModule(Module &M) override
    {
      LLVMContext &C = M.getContext();
      IntegerType *Int64Ty = Type::getInt64Ty(C);
      std::map<std::string, std::vector<Function *>> fileFunctionMap;
	    this->writer.Reset(this->s);
      this->writer.StartObject();

      for (Function &F : M)
      {
        if (F.isDeclaration())
        {
          continue;
        }

        // Create a global array for each function
        unsigned int NumBBs = std::distance(F.begin(), F.end());
        ArrayType *ArrayTy = ArrayType::get(Int64Ty, NumBBs);
        std::string counterName  = F.getName().str() + "_counters";
        llvm::dbgs() << "Creating Function Array: " << counterName << "\n";
        // GlobalVariable *BBCounters = dyn_cast<GlobalVariable>(M.getOrInsertGlobal(funcName, ArrayTy));
        auto *initializer = ConstantAggregateZero::get(ArrayTy);
        GlobalVariable *BBCounters = new GlobalVariable(M, ArrayTy, false, GlobalValue::InternalLinkage, initializer, counterName);

        this->writer.Key(F.getName().str().c_str());

        // Insert atomic increment operations in each basic block
        insertAtomicIncrements(F, BBCounters);              

        // Group functions by file name
        if (DISubprogram *SP = F.getSubprogram())
        {
          std::string FileName = SP->getFile()->getFilename().str();
          fileFunctionMap[FileName].push_back(&F);
        } else {
          llvm_unreachable("Function does not have a DISubprogram");
        }
      }

      // Insert calls to bc_cov_set_file and bc_cov
      insertbcCovCalls(M, fileFunctionMap);
      this->writer.EndObject();

      // Write the output to a file
      std::string output = this->s.GetString();
      // llvm::dbgs() << output << "\n";

      std::ofstream out(OutputFilename);
      out << output;
      out.close();

      return true;
    }

    void AddBasicBlockCoverage(BasicBlock *BB)
    {
      this->writer.Key("Coverage");
      this->writer.StartArray();

      std::set<std::tuple<std::string, uint32_t>> covinfo;
       
      for (Instruction &I : *BB) {
        if (const llvm::DebugLoc &DL = I.getDebugLoc()) {
          std::string filename = DL->getFilename().str();
          uint32_t line = DL->getLine();
          covinfo.insert(std::make_tuple(filename, line));
        }
      }

      for (auto &info : covinfo) {
        this->writer.StartObject();
        this->writer.Key("File");
        this->writer.String(std::get<0>(info).c_str());
        this->writer.Key("Line");
        this->writer.Uint(std::get<1>(info));
        this->writer.EndObject();
      }

      this->writer.EndArray();
    }

    void insertAtomicIncrements(Function &F, GlobalVariable *BBCounters)
    {
      unsigned int BBIndex = 0;
      this->writer.StartArray();
      
      for (BasicBlock &BB : F)
      {
        Instruction *InsI = &(*(BB.getFirstInsertionPt()));
        IRBuilder<> Builder(InsI);
        LLVMContext &C = BB.getContext();

        this->writer.StartObject();
        this->writer.Key("Id");
        this->writer.Uint(BBIndex);
        AddBasicBlockCoverage(&BB);
        this->writer.EndObject();

        // Create an atomic increment for the corresponding counter
        std::vector<Value *> Indices{ConstantInt::get(Type::getInt64Ty(C), 0), ConstantInt::get(Type::getInt64Ty(C), BBIndex++)};
        Value *Ptr = Builder.CreateInBoundsGEP(BBCounters, Indices);
        LoadInst *LoadedVal = Builder.CreateAlignedLoad(Type::getInt64Ty(C), Ptr, 8);
        LoadedVal->setAtomic(AtomicOrdering::Monotonic);
        Value *IncVal = Builder.CreateAdd(LoadedVal, ConstantInt::get(Type::getInt64Ty(C), 1));
        StoreInst *Store = Builder.CreateAlignedStore(IncVal, Ptr, 8);
        Store->setAtomic(AtomicOrdering::Monotonic);
      }

      this->writer.EndArray();
    }

    void insertbcCovCalls(Module &M, std::map<std::string, std::vector<Function *>> &fileFunctionMap)
    {
      LLVMContext &C = M.getContext();
      // create a new function named _bc_cov_dump 
      FunctionType *funcType = FunctionType::get(Type::getVoidTy(C), false);
      Function *DumpFunc = Function::Create(funcType, Function::ExternalLinkage, "_bc_dump_cov", &M);

      BasicBlock *BB = BasicBlock::Create(C, "entry", DumpFunc);
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
          std::string funcName = F->getName().str() + "_counters";
          llvm::dbgs() << "Finding array : " << funcName << "\n";
          GlobalVariable *BBCounters = M.getGlobalVariable(funcName, true);
          unsigned int NumBBs = std::distance(F->begin(), F->end());

          // Insert call to bc_cov
          insertCovCall(M, *F, BBCounters, NumBBs, builder);
        }
      }

      builder.CreateRetVoid();
    }

    void insertSetFileCall(Module &M, const std::string &fileName, int numFuncs, IRBuilder<> &Builder)
    {
      LLVMContext &C = M.getContext();
      FunctionType *SetFileType = FunctionType::get(Type::getVoidTy(C), 
          {Type::getInt8PtrTy(C), Type::getInt32Ty(C), Type::getInt32Ty(C)}, false);
      FunctionCallee SetFileFunc = M.getOrInsertFunction("bc_cov_set_file", SetFileType);

      // Create arguments for the call
      Constant *FileNameStr = Builder.CreateGlobalStringPtr(fileName);
      Value *FileNameLen = Builder.getInt32(fileName.length());
      Value *NumFuncsVal = Builder.getInt32(numFuncs);

      Builder.CreateCall(SetFileFunc, {FileNameStr, FileNameLen, NumFuncsVal});
    }

    void insertCovCall(Module &M, Function &F, GlobalVariable *BBCounters, unsigned int NumBBs, IRBuilder<> &Builder)
    {
      assert (BBCounters != nullptr && "Global Variable, needed to insert coverage is null");
      LLVMContext &C = M.getContext();
      FunctionType *CovFuncType = FunctionType::get(Type::getVoidTy(C), 
          {Type::getInt8PtrTy(C), Type::getInt32Ty(C), Type::getInt64PtrTy(C), Type::getInt32Ty(C)}, false);
      FunctionCallee CovFunc = M.getOrInsertFunction("bc_cov", CovFuncType);

      // Create arguments for the call
      Constant *FuncNameStr = Builder.CreateGlobalStringPtr(F.getName());
      Value *FuncNameLen = Builder.getInt32(F.getName().size());
      Value *NumBBsVal = Builder.getInt32(NumBBs);
      Value *CastedGlob = Builder.CreateBitCast(BBCounters, Type::getInt64PtrTy(C));

      llvm::dbgs() << "Function name: " << F.getName() << "\n";
      
      llvm::dbgs() << "Function name length: " << F.getName().size() << "\n";
      llvm::dbgs() << "Number of basic blocks: " << NumBBs << "\n";
      // BBCounters->dump();

      // F.dump();

      Builder.CreateCall(CovFunc, {FuncNameStr, FuncNameLen, CastedGlob, NumBBsVal});
    }
  };
} // namespace

  char CovInstrument::ID = 0;
  static RegisterPass<CovInstrument> X("cov-instrument", "Thread-Safe Coverage Instrumentation Pass", false, false);
