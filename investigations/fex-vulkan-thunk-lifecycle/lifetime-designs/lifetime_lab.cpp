#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <iostream>
#include <memory>
#include <mutex>
#include <optional>
#include <shared_mutex>
#include <sstream>
#include <string>
#include <thread>
#include <unordered_map>
#include <utility>
#include <vector>

using namespace std::chrono_literals;

enum class Outcome { Executed, Rejected, UAF, Conflict };
static const char* outcome_name(Outcome o) {
  switch (o) {
    case Outcome::Executed: return "EXEC";
    case Outcome::Rejected: return "REJECT";
    case Outcome::UAF: return "UAF";
    case Outcome::Conflict: return "CONFLICT";
  }
  return "?";
}

struct Mapping {
  uint64_t id{};
  uint64_t generation{};
  uintptr_t base{};
  std::string dso;
  std::atomic<bool> live{true};
};

struct OwnerState {
  uint64_t id{};
  uint64_t generation{};
  std::string dso;
  std::shared_ptr<Mapping> mapping;
  mutable std::mutex lease_m;
  std::condition_variable lease_cv;
  bool draining{};
  size_t active{};
  bool close_requested{};
};

struct Target {
  std::shared_ptr<OwnerState> owner;
  uintptr_t pc{};
  std::string abi;
  std::string alias;
};

struct Binding {
  uintptr_t native{};
  Target target;
};

static Outcome execute_raw(const Target& t) {
  return t.owner->mapping->live.load(std::memory_order_acquire) ? Outcome::Executed : Outcome::UAF;
}

struct CompiledCall {
  std::function<Outcome()> call;
};
struct CallbackHandle {
  std::function<Outcome()> call;
};

struct Stats {
  size_t registry_entries{};
  size_t callback_entries{};
  size_t host_slots{};
  size_t live_guest_mappings{};
  size_t close_requested_live{};
};

class Design {
public:
  virtual ~Design() = default;
  virtual std::string name() const = 0;
  virtual std::shared_ptr<OwnerState> load(const std::string& dso, uintptr_t base) = 0;
  virtual bool register_pfn(const std::shared_ptr<OwnerState>& owner, uintptr_t native,
                            std::string alias, std::string abi, uintptr_t offset) = 0;
  virtual CallbackHandle register_callback(const std::shared_ptr<OwnerState>& owner, uintptr_t offset) = 0;
  virtual Outcome dispatch(uintptr_t native) = 0;
  virtual Outcome dispatch_with_hook(uintptr_t native, const std::function<void()>& hook) = 0;
  virtual CompiledCall compile(uintptr_t native) = 0;
  virtual void unload(const std::shared_ptr<OwnerState>& owner) = 0;
  virtual Stats stats() const = 0;
  virtual std::vector<std::string> last_events() const = 0;
};

class BaseDesign : public Design {
protected:
  mutable std::mutex owners_m_;
  std::vector<std::shared_ptr<OwnerState>> owners_;
  std::atomic<uint64_t> next_owner_{1};
  std::atomic<uint64_t> next_generation_{1};
  mutable std::mutex events_m_;
  std::vector<std::string> events_;

  std::shared_ptr<OwnerState> make_owner(const std::string& dso, uintptr_t base) {
    auto owner = std::make_shared<OwnerState>();
    owner->id = next_owner_.fetch_add(1);
    owner->generation = next_generation_.fetch_add(1);
    owner->dso = dso;
    owner->mapping = std::make_shared<Mapping>();
    owner->mapping->id = owner->id;
    owner->mapping->generation = owner->generation;
    owner->mapping->base = base;
    owner->mapping->dso = dso;
    {
      std::lock_guard lk(owners_m_);
      owners_.push_back(owner);
    }
    return owner;
  }

  void clear_events() {
    std::lock_guard lk(events_m_);
    events_.clear();
  }
  void event(std::string e) {
    std::lock_guard lk(events_m_);
    events_.push_back(std::move(e));
  }
  size_t live_mappings() const {
    std::lock_guard lk(owners_m_);
    return std::count_if(owners_.begin(), owners_.end(), [](const auto& o) {
      return o->mapping->live.load(std::memory_order_acquire);
    });
  }
  size_t close_requested_live() const {
    std::lock_guard lk(owners_m_);
    return std::count_if(owners_.begin(), owners_.end(), [](const auto& o) {
      return o->close_requested && o->mapping->live.load(std::memory_order_acquire);
    });
  }

public:
  std::shared_ptr<OwnerState> load(const std::string& dso, uintptr_t base) override {
    return make_owner(dso, base);
  }
  std::vector<std::string> last_events() const override {
    std::lock_guard lk(events_m_);
    return events_;
  }
};

// 1) Minimal unload-owned deregistration. Only the native-PFN CustomIR table is owned.
class DeregisterDesign final : public BaseDesign {
  mutable std::mutex m_;
  std::unordered_map<uintptr_t, Binding> active_;
  std::vector<Target> callbacks_; // Existing host trampolines remain raw and unowned.
public:
  std::string name() const override { return "deregister"; }
  bool register_pfn(const std::shared_ptr<OwnerState>& o, uintptr_t n, std::string a, std::string abi, uintptr_t off) override {
    std::lock_guard lk(m_);
    auto it = active_.find(n);
    if (it != active_.end() && it->second.target.abi != abi) return false;
    active_[n] = Binding{n, Target{o, o->mapping->base + off, std::move(abi), std::move(a)}};
    return true;
  }
  CallbackHandle register_callback(const std::shared_ptr<OwnerState>& o, uintptr_t off) override {
    Target t{o, o->mapping->base + off, "callback", "callback"};
    { std::lock_guard lk(m_); callbacks_.push_back(t); }
    return CallbackHandle{[t] { return execute_raw(t); }};
  }
  Outcome dispatch(uintptr_t n) override {
    Target t;
    { std::lock_guard lk(m_); auto it=active_.find(n); if(it==active_.end()) return Outcome::Rejected; t=it->second.target; }
    return execute_raw(t);
  }
  Outcome dispatch_with_hook(uintptr_t n, const std::function<void()>& hook) override {
    Target t;
    { std::lock_guard lk(m_); auto it=active_.find(n); if(it==active_.end()) return Outcome::Rejected; t=it->second.target; }
    hook();
    return execute_raw(t);
  }
  CompiledCall compile(uintptr_t n) override {
    Target t;
    { std::lock_guard lk(m_); auto it=active_.find(n); if(it==active_.end()) return {{[]{return Outcome::Rejected;}}}; t=it->second.target; }
    return {{[t]{ return execute_raw(t); }}};
  }
  void unload(const std::shared_ptr<OwnerState>& o) override {
    clear_events(); event("registry_invalidate");
    { std::lock_guard lk(m_); for (auto it=active_.begin(); it!=active_.end();) { if(it->second.target.owner->id==o->id) it=active_.erase(it); else ++it; } }
    event("unmap"); o->mapping->live.store(false, std::memory_order_release);
  }
  Stats stats() const override {
    std::lock_guard lk(m_); return {active_.size(), callbacks_.size(), 0, live_mappings(), close_requested_live()};
  }
};

// 2) DSO ownership with a per-native stack and bulk removal.
class BulkOwnerDesign final : public BaseDesign {
  mutable std::mutex m_;
  std::unordered_map<uintptr_t, std::vector<Binding>> stacks_;
  std::unordered_map<uint64_t, std::vector<uintptr_t>> owner_keys_;
  std::unordered_map<uint64_t, std::vector<Target>> owner_callbacks_;
public:
  std::string name() const override { return "bulk_owner"; }
  bool register_pfn(const std::shared_ptr<OwnerState>& o, uintptr_t n, std::string a, std::string abi, uintptr_t off) override {
    std::lock_guard lk(m_); auto& s=stacks_[n]; if(!s.empty() && s.back().target.abi!=abi) return false;
    s.push_back({n, Target{o,o->mapping->base+off,std::move(abi),std::move(a)}}); owner_keys_[o->id].push_back(n); return true;
  }
  CallbackHandle register_callback(const std::shared_ptr<OwnerState>& o, uintptr_t off) override {
    Target t{o,o->mapping->base+off,"callback","callback"}; {std::lock_guard lk(m_); owner_callbacks_[o->id].push_back(t);} return {{[t]{return execute_raw(t);}}};
  }
  std::optional<Target> current(uintptr_t n) const {
    std::lock_guard lk(m_); auto it=stacks_.find(n); if(it==stacks_.end()||it->second.empty()) return {}; return it->second.back().target;
  }
  Outcome dispatch(uintptr_t n) override { auto t=current(n); return t?execute_raw(*t):Outcome::Rejected; }
  Outcome dispatch_with_hook(uintptr_t n,const std::function<void()>& hook) override {auto t=current(n);if(!t)return Outcome::Rejected;hook();return execute_raw(*t);}  
  CompiledCall compile(uintptr_t n) override {auto t=current(n); if(!t)return {{[]{return Outcome::Rejected;}}}; return {{[t=*t]{return execute_raw(t);}}};}
  void unload(const std::shared_ptr<OwnerState>& o) override {
    clear_events(); event("registry_invalidate");
    { std::lock_guard lk(m_); for(auto& [n,s]:stacks_) s.erase(std::remove_if(s.begin(),s.end(),[&](auto& b){return b.target.owner->id==o->id;}),s.end());
      for(auto it=stacks_.begin();it!=stacks_.end();) if(it->second.empty()) it=stacks_.erase(it); else ++it;
      owner_keys_.erase(o->id); owner_callbacks_.erase(o->id); }
    event("unmap"); o->mapping->live.store(false,std::memory_order_release);
  }
  Stats stats() const override {std::lock_guard lk(m_); size_t n=0,cb=0;for(auto&[_,s]:stacks_)n+=s.size();for(auto&[_,v]:owner_callbacks_)cb+=v.size();return{n,cb,0,live_mappings(),close_requested_live()};}
};

struct Slot {
  mutable std::mutex m;
  std::vector<Binding> stack;
  std::optional<Binding> current() const {std::lock_guard lk(m);if(stack.empty())return{};return stack.back();}
  bool add(Binding b){std::lock_guard lk(m);if(!stack.empty()&&stack.back().target.abi!=b.target.abi)return false;stack.push_back(std::move(b));return true;}
  void remove_owner(uint64_t id){std::lock_guard lk(m);stack.erase(std::remove_if(stack.begin(),stack.end(),[&](auto&b){return b.target.owner->id==id;}),stack.end());}
  bool empty() const {std::lock_guard lk(m);return stack.empty();}
};

struct CallbackSlot {
  mutable std::mutex m;
  std::optional<Target> target;
  std::optional<Target> get() const {std::lock_guard lk(m);return target;}
  void clear(){std::lock_guard lk(m);target.reset();}
};

// 3) Stable indirection slots; raw guest PCs are loaded from slots at execution time.
class StableSlotDesign final : public BaseDesign {
  mutable std::mutex m_;
  std::unordered_map<uintptr_t,std::shared_ptr<Slot>> slots_;
  std::unordered_map<uint64_t,std::vector<std::shared_ptr<CallbackSlot>>> callbacks_;
public:
  std::string name() const override{return "stable_slot";}
  bool register_pfn(const std::shared_ptr<OwnerState>&o,uintptr_t n,std::string a,std::string abi,uintptr_t off)override{
    std::shared_ptr<Slot>s;{std::lock_guard lk(m_);auto&x=slots_[n];if(!x)x=std::make_shared<Slot>();s=x;}return s->add({n,Target{o,o->mapping->base+off,std::move(abi),std::move(a)}});
  }
  CallbackHandle register_callback(const std::shared_ptr<OwnerState>&o,uintptr_t off)override{
    auto s=std::make_shared<CallbackSlot>();s->target=Target{o,o->mapping->base+off,"callback","callback"};{std::lock_guard lk(m_);callbacks_[o->id].push_back(s);}return{{[s]{auto t=s->get();return t?execute_raw(*t):Outcome::Rejected;}}};
  }
  std::shared_ptr<Slot> getslot(uintptr_t n)const{std::lock_guard lk(m_);auto it=slots_.find(n);return it==slots_.end()?nullptr:it->second;}
  Outcome dispatch(uintptr_t n)override{auto s=getslot(n);if(!s)return Outcome::Rejected;auto b=s->current();return b?execute_raw(b->target):Outcome::Rejected;}
  Outcome dispatch_with_hook(uintptr_t n,const std::function<void()>&hook)override{auto s=getslot(n);if(!s)return Outcome::Rejected;auto b=s->current();if(!b)return Outcome::Rejected;hook();return execute_raw(b->target);}  
  CompiledCall compile(uintptr_t n)override{auto s=getslot(n);if(!s)return{{[]{return Outcome::Rejected;}}};return{{[s]{auto b=s->current();return b?execute_raw(b->target):Outcome::Rejected;}}};}
  void unload(const std::shared_ptr<OwnerState>&o)override{
    clear_events();event("slot_invalidate");
    {std::lock_guard lk(m_);for(auto&[_,s]:slots_)s->remove_owner(o->id);if(auto it=callbacks_.find(o->id);it!=callbacks_.end()){for(auto&s:it->second)s->clear();callbacks_.erase(it);}}
    event("unmap");o->mapping->live.store(false,std::memory_order_release);
  }
  Stats stats()const override{std::lock_guard lk(m_);size_t entries=0,cb=0;for(auto&[_,s]:slots_){std::lock_guard sl(s->m);entries+=s->stack.size();}for(auto&[_,v]:callbacks_)cb+=v.size();return{entries,cb,slots_.size(),live_mappings(),close_requested_live()};}
};

// 4) Load-generation guards. Cached code carries the generation and validates it every entry.
class GenerationDesign final : public BaseDesign {
  mutable std::mutex m_;
  std::unordered_map<uintptr_t,std::vector<Binding>> stacks_;
  std::unordered_map<uint64_t,std::vector<std::weak_ptr<CallbackSlot>>> callbacks_;
  std::optional<Binding> current(uintptr_t n)const{std::lock_guard lk(m_);auto it=stacks_.find(n);if(it==stacks_.end()||it->second.empty())return{};return it->second.back();}
  bool generation_live(const Binding& b)const{
    std::lock_guard lk(m_);auto it=stacks_.find(b.native);if(it==stacks_.end()||it->second.empty())return false;auto&cur=it->second.back();return cur.target.owner->generation==b.target.owner->generation && cur.target.owner->mapping->live.load(std::memory_order_acquire);
  }
public:
  std::string name()const override{return "generation";}
  bool register_pfn(const std::shared_ptr<OwnerState>&o,uintptr_t n,std::string a,std::string abi,uintptr_t off)override{std::lock_guard lk(m_);auto&s=stacks_[n];if(!s.empty()&&s.back().target.abi!=abi)return false;s.push_back({n,Target{o,o->mapping->base+off,std::move(abi),std::move(a)}});return true;}
  CallbackHandle register_callback(const std::shared_ptr<OwnerState>&o,uintptr_t off)override{
    auto s=std::make_shared<CallbackSlot>();s->target=Target{o,o->mapping->base+off,"callback","callback"};{std::lock_guard lk(m_);callbacks_[o->id].push_back(s);}auto gen=o->generation;return{{[s,gen]{auto t=s->get();if(!t)return Outcome::Rejected;if(t->owner->generation!=gen||!t->owner->mapping->live.load(std::memory_order_acquire))return Outcome::Rejected;return execute_raw(*t);}}};
  }
  Outcome dispatch(uintptr_t n)override{auto b=current(n);if(!b)return Outcome::Rejected;if(!generation_live(*b))return Outcome::Rejected;return execute_raw(b->target);}  
  Outcome dispatch_with_hook(uintptr_t n,const std::function<void()>&hook)override{auto b=current(n);if(!b)return Outcome::Rejected;if(!generation_live(*b))return Outcome::Rejected;hook();return execute_raw(b->target);}  
  CompiledCall compile(uintptr_t n)override{auto b=current(n);if(!b)return{{[]{return Outcome::Rejected;}}};return{{[this,b=*b]{if(!generation_live(b))return Outcome::Rejected;return execute_raw(b.target);}}};}
  void unload(const std::shared_ptr<OwnerState>&o)override{
    clear_events();event("generation_dead");{std::lock_guard lk(m_);for(auto&[_,s]:stacks_)s.erase(std::remove_if(s.begin(),s.end(),[&](auto&b){return b.target.owner->id==o->id;}),s.end());for(auto it=stacks_.begin();it!=stacks_.end();)if(it->second.empty())it=stacks_.erase(it);else++it;if(auto it=callbacks_.find(o->id);it!=callbacks_.end()){for(auto&w:it->second)if(auto s=w.lock())s->clear();callbacks_.erase(it);}}
    event("unmap");o->mapping->live.store(false,std::memory_order_release);
  }
  Stats stats()const override{std::lock_guard lk(m_);size_t n=0;for(auto&[_,s]:stacks_)n+=s.size();size_t cb=0;for(auto&[_,v]:callbacks_)cb+=v.size();return{n,cb,0,live_mappings(),close_requested_live()};}
};

// 5) Per-dispatch stale target rejection against live mappings, with stale registry rows retained.
class StaleRejectDesign final : public BaseDesign {
  mutable std::mutex m_;
  std::unordered_map<uintptr_t,std::vector<Binding>> rows_;
  std::vector<Target> callbacks_;
  std::optional<Binding> current_live(uintptr_t n)const{std::lock_guard lk(m_);auto it=rows_.find(n);if(it==rows_.end())return{};for(auto r=it->second.rbegin();r!=it->second.rend();++r)if(r->target.owner->mapping->live.load(std::memory_order_acquire))return *r;return{};}
public:
  std::string name()const override{return "stale_reject";}
  bool register_pfn(const std::shared_ptr<OwnerState>&o,uintptr_t n,std::string a,std::string abi,uintptr_t off)override{std::lock_guard lk(m_);auto&s=rows_[n];for(auto r=s.rbegin();r!=s.rend();++r)if(r->target.owner->mapping->live.load()&&r->target.abi!=abi)return false;s.push_back({n,Target{o,o->mapping->base+off,std::move(abi),std::move(a)}});return true;}
  CallbackHandle register_callback(const std::shared_ptr<OwnerState>&o,uintptr_t off)override{Target t{o,o->mapping->base+off,"callback","callback"};{std::lock_guard lk(m_);callbacks_.push_back(t);}return{{[t]{if(!t.owner->mapping->live.load(std::memory_order_acquire))return Outcome::Rejected;return execute_raw(t);}}};}
  Outcome dispatch(uintptr_t n)override{auto b=current_live(n);return b?execute_raw(b->target):Outcome::Rejected;}
  Outcome dispatch_with_hook(uintptr_t n,const std::function<void()>&hook)override{auto b=current_live(n);if(!b)return Outcome::Rejected;hook();return execute_raw(b->target);}  
  CompiledCall compile(uintptr_t n)override{auto b=current_live(n);if(!b)return{{[]{return Outcome::Rejected;}}};Target t=b->target;return{{[t]{return execute_raw(t);}}};}
  void unload(const std::shared_ptr<OwnerState>&o)override{clear_events();event("unmap");o->mapping->live.store(false,std::memory_order_release);}
  Stats stats()const override{std::lock_guard lk(m_);size_t n=0;for(auto&[_,s]:rows_)n+=s.size();return{n,callbacks_.size(),0,live_mappings(),close_requested_live()};}
};

// 6) Pin/refcount lifetime. Close requests leave any referenced guest thunk resident.
class PinDesign final : public BaseDesign {
  mutable std::mutex m_;
  std::unordered_map<std::string,std::weak_ptr<OwnerState>> resident_by_name_;
  std::unordered_map<uintptr_t,std::vector<Binding>> rows_;
  std::vector<Target> callbacks_;
public:
  std::string name()const override{return "pin_refcount";}
  std::shared_ptr<OwnerState> load(const std::string&dso,uintptr_t base)override{
    std::lock_guard lk(m_);if(auto it=resident_by_name_.find(dso);it!=resident_by_name_.end())if(auto o=it->second.lock())if(o->mapping->live.load())return o;auto o=make_owner(dso,base);resident_by_name_[dso]=o;return o;
  }
  bool register_pfn(const std::shared_ptr<OwnerState>&o,uintptr_t n,std::string a,std::string abi,uintptr_t off)override{std::lock_guard lk(m_);auto&s=rows_[n];if(!s.empty()&&s.back().target.abi!=abi)return false;s.push_back({n,Target{o,o->mapping->base+off,std::move(abi),std::move(a)}});return true;}
  CallbackHandle register_callback(const std::shared_ptr<OwnerState>&o,uintptr_t off)override{Target t{o,o->mapping->base+off,"callback","callback"};{std::lock_guard lk(m_);callbacks_.push_back(t);}return{{[t]{return execute_raw(t);}}};}
  std::optional<Target> current(uintptr_t n)const{std::lock_guard lk(m_);auto it=rows_.find(n);if(it==rows_.end()||it->second.empty())return{};return it->second.back().target;}
  Outcome dispatch(uintptr_t n)override{auto t=current(n);return t?execute_raw(*t):Outcome::Rejected;}
  Outcome dispatch_with_hook(uintptr_t n,const std::function<void()>&hook)override{auto t=current(n);if(!t)return Outcome::Rejected;hook();return execute_raw(*t);}  
  CompiledCall compile(uintptr_t n)override{auto t=current(n);if(!t)return{{[]{return Outcome::Rejected;}}};return{{[t=*t]{return execute_raw(t);}}};}
  void unload(const std::shared_ptr<OwnerState>&o)override{clear_events();event("close_deferred_pin");o->close_requested=true;/* retained */}
  Stats stats()const override{std::lock_guard lk(m_);size_t n=0;for(auto&[_,s]:rows_)n+=s.size();return{n,callbacks_.size(),0,live_mappings(),close_requested_live()};}
};

// 7) Stable slots + load-generation ownership + an in-flight lease. This is the combined candidate.
class LeaseSlotDesign final : public BaseDesign {
  mutable std::mutex m_;
  std::unordered_map<uintptr_t,std::shared_ptr<Slot>> slots_;
  std::unordered_map<uint64_t,std::vector<std::shared_ptr<CallbackSlot>>> callbacks_;

  struct Lease {
    std::shared_ptr<OwnerState> owner;
    bool held{};
    Lease()=default;
    explicit Lease(std::shared_ptr<OwnerState> o):owner(std::move(o)) {
      std::unique_lock lk(owner->lease_m);
      if(!owner->draining && owner->mapping->live.load(std::memory_order_acquire)){++owner->active;held=true;}
    }
    Lease(const Lease&)=delete; Lease&operator=(const Lease&)=delete;
    Lease(Lease&&x)noexcept:owner(std::move(x.owner)),held(std::exchange(x.held,false)){}
    ~Lease(){release();}
    void release(){if(!held)return;std::unique_lock lk(owner->lease_m);--owner->active;held=false;if(owner->active==0)owner->lease_cv.notify_all();}
  };

  std::shared_ptr<Slot> getslot(uintptr_t n)const{std::lock_guard lk(m_);auto it=slots_.find(n);return it==slots_.end()?nullptr:it->second;}
  Outcome run_binding(const Binding&b,const std::function<void()>&hook={}){
    Lease lease{b.target.owner};if(!lease.held)return Outcome::Rejected;if(hook)hook();return execute_raw(b.target);
  }
public:
  std::string name()const override{return "lease_slot";}
  bool register_pfn(const std::shared_ptr<OwnerState>&o,uintptr_t n,std::string a,std::string abi,uintptr_t off)override{
    std::shared_ptr<Slot>s;{std::lock_guard lk(m_);auto&x=slots_[n];if(!x)x=std::make_shared<Slot>();s=x;}return s->add({n,Target{o,o->mapping->base+off,std::move(abi),std::move(a)}});
  }
  CallbackHandle register_callback(const std::shared_ptr<OwnerState>&o,uintptr_t off)override{
    auto s=std::make_shared<CallbackSlot>();s->target=Target{o,o->mapping->base+off,"callback","callback"};{std::lock_guard lk(m_);callbacks_[o->id].push_back(s);}return{{[this,s]{auto t=s->get();if(!t)return Outcome::Rejected;Binding b{0,*t};return run_binding(b);}}};
  }
  Outcome dispatch(uintptr_t n)override{auto s=getslot(n);if(!s)return Outcome::Rejected;auto b=s->current();return b?run_binding(*b):Outcome::Rejected;}
  Outcome dispatch_with_hook(uintptr_t n,const std::function<void()>&hook)override{auto s=getslot(n);if(!s)return Outcome::Rejected;auto b=s->current();return b?run_binding(*b,hook):Outcome::Rejected;}
  CompiledCall compile(uintptr_t n)override{auto s=getslot(n);if(!s)return{{[]{return Outcome::Rejected;}}};return{{[this,s]{auto b=s->current();return b?run_binding(*b):Outcome::Rejected;}}};}
  void unload(const std::shared_ptr<OwnerState>&o)override{
    clear_events();
    {std::unique_lock lk(o->lease_m);o->draining=true;}
    event("generation_draining");
    event("slot_invalidate");
    {
      std::lock_guard lk(m_);
      for(auto&[_,s]:slots_)s->remove_owner(o->id);
      if(auto it=callbacks_.find(o->id);it!=callbacks_.end()){for(auto&s:it->second)s->clear();callbacks_.erase(it);}
    }
    event("code_cache_invalidate");
    {std::unique_lock lk(o->lease_m);o->lease_cv.wait(lk,[&]{return o->active==0;});}
    event("drain_complete");
    o->mapping->live.store(false,std::memory_order_release);event("unmap");
    {std::lock_guard lk(m_);for(auto it=slots_.begin();it!=slots_.end();)if(it->second->empty())it=slots_.erase(it);else++it;}
  }
  Stats stats()const override{std::lock_guard lk(m_);size_t n=0,cb=0;for(auto&[_,s]:slots_){std::lock_guard sl(s->m);n+=s->stack.size();}for(auto&[_,v]:callbacks_)cb+=v.size();return{n,cb,slots_.size(),live_mappings(),close_requested_live()};}
};

using Factory=std::function<std::unique_ptr<Design>()>;
struct TestResult{std::string test;bool pass;std::string detail;};
static std::string detail_out(Outcome o){return outcome_name(o);} 

static TestResult t_unload_reload(const Factory&f){auto d=f();auto a=d->load("vulkan",0x100000);d->register_pfn(a,0x9000,"vkA","abi",0x100);auto before=d->dispatch(0x9000);d->unload(a);auto after=d->dispatch(0x9000);auto b=d->load("vulkan",0x300000);d->register_pfn(b,0x9000,"vkA","abi",0x100);auto re=d->dispatch(0x9000);bool p=before==Outcome::Executed&&after==Outcome::Rejected&&re==Outcome::Executed&&b->mapping->base==0x300000;std::ostringstream s;s<<"before="<<outcome_name(before)<<", after_close="<<outcome_name(after)<<", reload="<<outcome_name(re)<<", base=0x"<<std::hex<<b->mapping->base;return{"unload_reload",p,s.str()};}
static TestResult t_same_pfn(const Factory&f){auto d=f();auto a=d->load("vulkan",0x100000);d->register_pfn(a,0x9000,"vkA","abi",0x100);auto g1=a->generation;d->unload(a);auto b=d->load("vulkan",0x300000);d->register_pfn(b,0x9000,"vkA","abi",0x180);auto o=d->dispatch(0x9000);bool p=o==Outcome::Executed&&b->generation!=g1;std::ostringstream s;s<<"dispatch="<<outcome_name(o)<<", gen1="<<g1<<", gen2="<<b->generation;return{"same_native_pfn_reused",p,s.str()};}
static TestResult t_diff_base(const Factory&f){auto d=f();auto a=d->load("vulkan",0x111000);d->register_pfn(a,0x9000,"vkA","abi",0x120);d->unload(a);auto b=d->load("vulkan",0x777000);d->register_pfn(b,0x9000,"vkA","abi",0x120);bool p=b->mapping->base==0x777000&&b->generation!=a->generation&&d->dispatch(0x9000)==Outcome::Executed;std::ostringstream s;s<<"old_base=0x"<<std::hex<<a->mapping->base<<", new_base=0x"<<b->mapping->base<<std::dec<<", old_gen="<<a->generation<<", new_gen="<<b->generation;return{"different_guest_load_bases",p,s.str()};}
static TestResult t_aliases(const Factory&f){auto d=f();auto a=d->load("dsoA",0x100000);auto b=d->load("dsoB",0x200000);bool r1=d->register_pfn(a,0x9000,"aliasA","abi",0x100);bool r2=d->register_pfn(b,0x9000,"aliasB","abi",0x200);auto top=d->dispatch(0x9000);d->unload(b);auto fallback=d->dispatch(0x9000);bool p=r1&&r2&&top==Outcome::Executed&&!b->mapping->live.load()&&fallback==Outcome::Executed;std::ostringstream s;s<<"regA="<<r1<<", regB="<<r2<<", newest="<<outcome_name(top)<<", B_unmapped="<<(!b->mapping->live.load())<<", after_unload_B="<<outcome_name(fallback);return{"aliases_one_native_address",p,s.str()};}
static TestResult t_alias_conflict(const Factory&f){auto d=f();auto a=d->load("A",0x100000);auto b=d->load("B",0x200000);bool r1=d->register_pfn(a,0x9000,"aliasA","abi1",0x100);bool r2=d->register_pfn(b,0x9000,"aliasB","abi2",0x200);return{"alias_abi_conflict_rejected",r1&&!r2,"first="+std::to_string(r1)+", incompatible_second="+std::to_string(r2)};}
static TestResult t_multi_dso(const Factory&f){auto d=f();auto a=d->load("A",0x100000);auto b=d->load("B",0x200000);d->register_pfn(a,0x9000,"a","a",0x100);d->register_pfn(b,0xA000,"b","b",0x100);d->unload(a);auto x=d->dispatch(0x9000),y=d->dispatch(0xA000);bool p=x==Outcome::Rejected&&y==Outcome::Executed;return{"multiple_thunk_dsos",p,"A_after="+detail_out(x)+", B_after="+detail_out(y)};}
static TestResult t_callback(const Factory&f){auto d=f();auto a=d->load("A",0x100000);auto cb=d->register_callback(a,0x500);auto before=cb.call();d->unload(a);auto after=cb.call();bool p=before==Outcome::Executed&&after==Outcome::Rejected;return{"host_to_guest_callback",p,"before="+detail_out(before)+", after_close="+detail_out(after)};}
static TestResult t_dynamic_pfn(const Factory&f){auto d=f();uintptr_t held=0x9000;auto a=d->load("vulkan",0x100000);d->register_pfn(a,held,"vkDyn","abi",0x100);auto first=d->dispatch(held);d->unload(a);auto b=d->load("vulkan",0x500000);d->register_pfn(b,held,"vkDyn","abi",0x300);auto second=d->dispatch(held);bool p=first==Outcome::Executed&&second==Outcome::Executed&&b->generation!=a->generation;return{"guest_to_host_dynamic_pfn",p,"held_pfn=0x9000, first="+detail_out(first)+", after_reload="+detail_out(second)};}
static TestResult t_code_cache(const Factory&f){auto d=f();auto a=d->load("A",0x100000);d->register_pfn(a,0x9000,"a","abi",0x100);auto c=d->compile(0x9000);auto before=c.call();d->unload(a);auto after=c.call();bool p=before==Outcome::Executed&&after==Outcome::Rejected;return{"code_cache_stale_target",p,"compiled_before="+detail_out(before)+", compiled_after_close="+detail_out(after)};}
static TestResult t_code_cache_reload(const Factory&f){auto d=f();auto a=d->load("A",0x100000);d->register_pfn(a,0x9000,"a","abi",0x100);auto c=d->compile(0x9000);d->unload(a);auto b=d->load("A",0x600000);d->register_pfn(b,0x9000,"a","abi",0x300);auto cached=c.call();auto fresh=d->dispatch(0x9000);bool p=!a->mapping->live.load()&&cached!=Outcome::UAF&&fresh==Outcome::Executed&&b->mapping->base==0x600000;std::ostringstream s;s<<"old_unmapped="<<(!a->mapping->live.load())<<", cached_after_reload="<<outcome_name(cached)<<", fresh="<<outcome_name(fresh)<<", new_base=0x"<<std::hex<<b->mapping->base;return{"code_cache_reload_same_pfn",p,s.str()};}
static TestResult t_metadata_growth(const Factory&f){auto d=f();for(int i=0;i<100;++i){auto o=d->load("cycle"+std::to_string(i),0x100000+i*0x10000);d->register_pfn(o,0x9000+i,"x","abi",0x100);d->unload(o);}auto st=d->stats();bool p=st.registry_entries==0&&st.callback_entries==0&&st.host_slots==0;std::ostringstream s;s<<"registry="<<st.registry_entries<<", callbacks="<<st.callback_entries<<", host_slots="<<st.host_slots;return{"metadata_growth_100_unique_pfns",p,s.str()};}
static TestResult t_concurrent(const Factory&f){auto d=f();auto a=d->load("A",0x100000);d->register_pfn(a,0x9000,"a","abi",0x100);std::mutex m;std::condition_variable cv;bool at_hook=false,allow=false,unload_done=false;Outcome call=Outcome::Rejected;
  std::thread caller([&]{call=d->dispatch_with_hook(0x9000,[&]{std::unique_lock lk(m);at_hook=true;cv.notify_all();cv.wait(lk,[&]{return allow;});});});
  {std::unique_lock lk(m);cv.wait(lk,[&]{return at_hook;});}
  std::thread closer([&]{d->unload(a);{std::lock_guard lk(m);unload_done=true;}cv.notify_all();});
  bool close_finished_while_call_paused;{std::unique_lock lk(m);close_finished_while_call_paused=cv.wait_for(lk,40ms,[&]{return unload_done;});allow=true;cv.notify_all();}
  caller.join();closer.join();bool unmapped=!a->mapping->live.load();bool p=call!=Outcome::UAF&&unmapped;std::ostringstream s;s<<"call="<<outcome_name(call)<<", close_completed_while_paused="<<close_finished_while_call_paused<<", unmapped="<<unmapped;return{"concurrent_unload_dispatch",p,s.str()};}
static TestResult t_order(const Factory&f){auto d=f();auto a=d->load("A",0x100000);d->register_pfn(a,0x9000,"a","abi",0x100);d->unload(a);auto ev=d->last_events();auto pos=[&](std::string x){auto it=std::find(ev.begin(),ev.end(),x);return it==ev.end()?size_t(-1):size_t(it-ev.begin());};size_t un=pos("unmap");size_t inv=std::min({pos("registry_invalidate"),pos("slot_invalidate"),pos("generation_dead")});bool p=un!=size_t(-1)&&inv!=size_t(-1)&&inv<un;std::ostringstream s;for(size_t i=0;i<ev.size();++i){if(i)s<<">";s<<ev[i];}if(ev.empty())s<<"(none)";return{"invalidation_before_unmap",p,s.str()};}
static TestResult t_stale_entries(const Factory&f){auto d=f();for(int i=0;i<100;++i){auto o=d->load("cycle"+std::to_string(i),0x100000+i*0x10000);d->register_pfn(o,0x9000+i,"x","abi",0x100);d->unload(o);}auto st=d->stats();bool p=st.registry_entries==0&&st.callback_entries==0;std::ostringstream s;s<<"registry="<<st.registry_entries<<", callbacks="<<st.callback_entries<<", host_slots="<<st.host_slots;return{"stale_entries_100_cycles",p,s.str()};}
static TestResult t_residency(const Factory&f){auto d=f();for(int i=0;i<40;++i){auto o=d->load("same",0x100000+i*0x20000);d->register_pfn(o,0x9000,"x","abi",0x100);d->unload(o);}auto st=d->stats();bool p=st.live_guest_mappings==0&&st.close_requested_live==0;std::ostringstream s;s<<"live_guest_mappings="<<st.live_guest_mappings<<", close_requested_live="<<st.close_requested_live<<", host_slots="<<st.host_slots;return{"guest_mapping_residency_40_cycles",p,s.str()};}

int main(){
  std::vector<std::pair<std::string,Factory>> designs={
    {"deregister",[]{return std::make_unique<DeregisterDesign>();}},
    {"bulk_owner",[]{return std::make_unique<BulkOwnerDesign>();}},
    {"stable_slot",[]{return std::make_unique<StableSlotDesign>();}},
    {"generation",[]{return std::make_unique<GenerationDesign>();}},
    {"stale_reject",[]{return std::make_unique<StaleRejectDesign>();}},
    {"pin_refcount",[]{return std::make_unique<PinDesign>();}},
    {"lease_slot",[]{return std::make_unique<LeaseSlotDesign>();}},
  };
  using TF=TestResult(*)(const Factory&);
  std::vector<TF> tests={t_unload_reload,t_same_pfn,t_diff_base,t_aliases,t_alias_conflict,t_multi_dso,t_callback,t_dynamic_pfn,t_code_cache,t_code_cache_reload,t_concurrent,t_order,t_stale_entries,t_metadata_growth,t_residency};
  std::cout<<"design\ttest\tresult\tdetail\n";
  for(auto&[name,f]:designs){for(auto t:tests){auto r=t(f);std::cout<<name<<"\t"<<r.test<<"\t"<<(r.pass?"PASS":"FAIL")<<"\t"<<r.detail<<"\n";}}
}
