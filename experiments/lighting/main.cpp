#include <juce_core/juce_core.h>
// The upstream runner's unqualified helper otherwise fails in client translation units.
namespace roli::littlefoot { using juce::readLittleEndianBitsInBuffer; }
#include <roli_blocks_basics/roli_blocks_basics.h>
#include <csignal>
#include <cstring>
#include <iostream>
#include <map>
#include <stdexcept>
#include <vector>

namespace lf = roli::littlefoot;

static volatile std::sig_atomic_t interrupted = 0;
static void handleInterrupt(int) { interrupted = 1; }

static void require(bool condition, const juce::String& message)
{
    if (!condition)
        throw std::runtime_error(message.toStdString());
}

static juce::String sourceFor(const juce::String& name)
{
    auto file = juce::File(ROLI_PROBE_SOURCE_DIR).getChildFile(name + ".littlefoot");
    require(file.existsAsFile(), "Missing probe source: " + file.getFullPathName());
    auto source = file.loadFileAsString();
    require(source.isNotEmpty(), "Empty probe source");
    return source;
}

struct Simulation
{
    int now = 0;
    std::vector<std::pair<bool, bool>> handlers;
    int pixels = 0;
    juce::String error;

    static lf::int32 clock(void* context, const lf::int32*)
    {
        return static_cast<Simulation*>(context)->now;
    }
    static lf::int32 handler(void* context, const lf::int32* args)
    {
        auto& simulation = *static_cast<Simulation*>(context);
        if (args[0] != 1)
            simulation.error = "Probe must NEVER disable native touch/MIDI";
        simulation.handlers.emplace_back(args[0] != 0, args[1] != 0);
        return 0;
    }
    static lf::int32 pixel(void* context, const lf::int32* args)
    {
        auto& simulation = *static_cast<Simulation*>(context);
        if (args[2] != 0 || args[1] != 24
                    || static_cast<juce::uint32>(args[0]) != 0xff4fc532u)
            simulation.error = "Unexpected pixel or green color";
        ++simulation.pixels;
        return 0;
    }
};

static void selfTest()
{
    // Only these native functions are allowed; MIDI/config/flash writes cannot compile.
    const lf::NativeFunction functions[] = {
        {"getMillisecondCounter/i", Simulation::clock},
        {"setUseDefaultKeyHandler/vbb", Simulation::handler},
        {"fillPixel/viii", Simulation::pixel}
    };
    for (const auto& name : {"recovery", "green-pulse"})
    {
        Simulation simulation;
        lf::Runner<16384, 2048> runner;
        runner.setNativeFunctions(functions, 3, &simulation);
        lf::Compiler compiler;
        compiler.addNativeFunctions(runner);
        auto result = compiler.compile(sourceFor(name), 0);
        require(result.wasOk(), result.getErrorMessage());
        require(compiler.compiledObjectCode.size() < 16384, "Probe is too large");
        std::memcpy(runner.getProgramAndDataStart(), compiler.compiledObjectCode.begin(),
                    static_cast<size_t>(compiler.compiledObjectCode.size()));
        auto call = [&](const char* signature) {
            decltype(runner)::FunctionExecutionContext context(runner, signature);
            int checks = 0;
            require(context.run([&] { return ++checks > 1000; }) == decltype(runner)::ErrorCode::ok,
                    juce::String("VM execution failed: ") + signature);
            require(simulation.error.isEmpty(), simulation.error);
        };
        call("initialise/v");
        const bool green = juce::String(name) == "green-pulse";
        require(simulation.handlers.back() == std::make_pair(true, !green),
                "Wrong initial handler state");
        for (int time : {0, 1000, 2999, 3000, 5000, 20000})
        {
            simulation.now = time;
            call("repaint/v");
            if (time >= 3000)
                require(simulation.handlers.back() == std::make_pair(true, true),
                        "Device watchdog did not restore native handling");
        }
        require(simulation.pixels == (green ? 3 : 0), "Unexpected painting after timeout");
        std::cout << name << ": compiled and VM-tested ("
                  << compiler.compiledObjectCode.size() << " bytes)\n";
    }
}

class ProbeProgram final : public roli::Block::Program
{
public:
    explicit ProbeProgram(roli::Block& block) : Program(block) {}
    juce::String getLittleFootProgram() override { return sourceFor("recovery"); }
};

class RecoveryProbe final : private roli::Block::ConfigItemListener,
                            private roli::Block::ProgramLoadedListener
{
public:
    RecoveryProbe(juce::String serial, juce::File backup)
        : serialNumber(std::move(serial)), backupFile(std::move(backup)), topology(true)
    {
    }

    ~RecoveryProbe() override
    {
        if (target != nullptr)
        {
            if (uploadAttempted && !defaultRestoreRequested)
                target->resetProgramToDefault();
            target->removeConfigItemListener(this);
            target->removeProgramLoadedListener(this);
        }
        topology.setActive(false);
    }

    void run(bool restoreOnly)
    {
        require(serialNumber.startsWith("RP4") && serialNumber.length() == 16
                    && serialNumber.containsOnly("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
                "An exact 16-character RP4 Piano serial is required");
        if (!restoreOnly)
            require(!backupFile.exists(), "Refusing to overwrite an existing recovery snapshot");
        topology.setActive(true);
        waitUntil([&] {
            for (auto block : topology.getBlocks())
                if (block->serialNumber == serialNumber)
                    target = block;
            return target != nullptr;
        }, 15000, "Piano not discovered; check USB connection and competing ROLI apps. No program uploaded");
        target->addConfigItemListener(this);
        target->addProgramLoadedListener(this);
        if (restoreOnly)
        {
            target->resetProgramToDefault();
            defaultRestoreRequested = true;
            std::cout << "Saved default-program restore requested. Awaiting configuration readback.\n";
            readConfig();
            std::cout << "Saved default-program restore requested; keyboard responds to config reads.\n"
                         "Confirm normal playing and lighting before reopening Live.\n";
            return;
        }
        readConfig();
        std::cout << "Configuration items received:";
        for (const auto& [id, state] : config)
            std::cout << ' ' << id;
        std::cout << '\n';
        require(config.count(20) && config.count(34) && config.count(35),
                "Incomplete keyboard lighting snapshot; refusing upload");
        const auto before = config;
        saveSnapshot();
        std::cout << "Snapshot saved. Loading temporary native-handler recovery probe.\n";
        uploadAttempted = true;
        auto result = target->setProgram(std::make_unique<ProbeProgram>(*target),
                                         roli::Block::ProgramPersistency::setAsTemp);
        require(result.wasOk(), result.getErrorMessage());
        waitUntil([&] { return loaded; }, 10000, "Temporary program upload not acknowledged");
        std::cout << "Temporary program acknowledged. Restoring saved default in 5 seconds.\n";
        const auto start = juce::Time::getMillisecondCounterHiRes();
        waitUntil([&] { return juce::Time::getMillisecondCounterHiRes() - start >= 5000; },
                  6000, "Probe hold timed out");
        target->resetProgramToDefault();
        defaultRestoreRequested = true;
        readConfig();
        require(config == before,
                "Keyboard configuration changed: retain the snapshot and investigate; "
                "do NOT proceed to green lighting");
        std::cout << "Default-program restore requested; configuration readback matches.\n"
                     "This is NOT visual/MPE verification: confirm normal playing and lighting.\n";
    }

private:
    using Config = std::map<juce::uint32, std::pair<juce::int32, bool>>;
    juce::String serialNumber;
    juce::File backupFile;
    roli::PhysicalTopologySource topology;
    roli::Block::Ptr target;
    Config config;
    bool synced = false, loaded = false, uploadAttempted = false, defaultRestoreRequested = false;

    template <typename Predicate>
    void waitUntil(Predicate ready, int timeout, const char* error)
    {
        const auto start = juce::Time::getMillisecondCounterHiRes();
        while (!ready())
        {
            require(!interrupted, "Interrupted: requesting default-program restoration");
            require(target == nullptr || target->isConnected(), "Piano disconnected");
            require(juce::Time::getMillisecondCounterHiRes() - start < timeout, error);
            juce::MessageManager::getInstance()->runDispatchLoopUntil(20);
        }
    }

    void readConfig()
    {
        config.clear();
        synced = false;
        target->requestFactoryConfigSync();
        waitUntil([&] { return synced; }, 10000, "Keyboard configuration readback timed out");
        require(!config.empty(),
                "Configuration sync ended without any setting values. "
                "Backup/restoration cannot be verified; no further uploads permitted.");
    }

    void saveSnapshot()
    {
        juce::DynamicObject::Ptr object = new juce::DynamicObject();
        object->setProperty("serial", target->serialNumber);
        object->setProperty("firmware", target->versionNumber);
        object->setProperty("captured_at", juce::Time::getCurrentTime().toISO8601(true));
        juce::Array<juce::var> items;
        for (const auto& [id, state] : config)
        {
            juce::DynamicObject::Ptr item = new juce::DynamicObject();
            item->setProperty("id", static_cast<int>(id));
            item->setProperty("value", static_cast<int>(state.first));
            item->setProperty("active", state.second);
            items.add(juce::var(item.get()));
        }
        object->setProperty("config", items);
        auto result = backupFile.getParentDirectory().createDirectory();
        require(result.wasOk(), result.getErrorMessage());
        auto text = juce::JSON::toString(juce::var(object.get()));
        require(backupFile.replaceWithText(text) && backupFile.loadFileAsString() == text,
                "Cannot persist recovery snapshot; refusing upload");
    }

    void handleConfigItemChanged(roli::Block&, const roli::Block::ConfigMetaData& item,
                                 juce::uint32 index) override
    {
        config[index] = {item.value, item.isActive};
    }
    void handleConfigSyncEnded(roli::Block&) override { synced = true; }
    void handleProgramLoaded(roli::Block&) override { loaded = true; }
};

int main(int argc, char** argv)
{
    try
    {
        if (argc == 2 && juce::String(argv[1]) == "--self-test")
        {
            selfTest();
            return 0;
        }
        const bool restoreOnly = argc == 3 && juce::String(argv[1]) == "--restore-default";
        require(restoreOnly || (argc == 4 && juce::String(argv[1]) == "--test-restore"),
                "Offline: --self-test\n"
                "Opt-in hardware test (quit Live first): --test-restore RP4_SERIAL /absolute/snapshot.json\n"
                "Recovery without uploading: --restore-default RP4_SERIAL\n"
                "Green-pulse upload is deliberately NOT exposed until recovery is hardware-verified.");
        if (!restoreOnly)
            require(juce::File::isAbsolutePath(argv[3]), "Snapshot path must be absolute");
       #if JUCE_MAC
        juce::ChildProcess liveCheck;
        require(liveCheck.start(juce::StringArray{"/usr/bin/pgrep", "-x", "Live"})
                    && liveCheck.waitForProcessToFinish(2000)
                    && liveCheck.getExitCode() == 1,
                "Quit Ableton Live before a hardware recovery test");
       #else
        require(false, "Hardware probe currently supports macOS only");
       #endif
        std::signal(SIGINT, handleInterrupt);
        std::signal(SIGTERM, handleInterrupt);
        selfTest();
        juce::ScopedJuceInitialiser_GUI initialise;
        RecoveryProbe probe(argv[2], restoreOnly ? juce::File() : juce::File(argv[3]));
        probe.run(restoreOnly);
        return 0;
    }
    catch (const std::exception& error)
    {
        std::cerr << "ERROR: " << error.what() << '\n';
        return 1;
    }
}
