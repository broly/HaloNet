using namespace std;

#include "Python.h"
#include <map>
#include <unordered_map>
#include <vector>
#include <string>

using namespace std;

unordered_map<string, unordered_map<string, PyObject*>> Types;

namespace TypeDatabaseAPI
{
    bool RegisterType(const char* ContextName, const char* TypeName, PyObject* InPythonObject)
    {
        auto it = Types.find(ContextName);
		if (it == Types.end())
		{
			Types.insert(pair<string, unordered_map<string, PyObject*>>(ContextName, {}));
			it = Types.find(ContextName);
		}

		auto t_it = it->second.find(TypeName);
		if (t_it == it->second.end())
		{
		    Py_INCREF(InPythonObject);
			it->second.insert(pair<string, PyObject*>(TypeName, InPythonObject));
			return true;
		}

		return false;
    };

    PyObject* FindType(const char* ContextName, const char* TypeName, PyObject* DefaultObject)
    {
        if (ContextName == nullptr)
        {
            for (auto& pair : Types)
            {
                for (auto& tpair : pair.second)
                {
                    if (tpair.first == TypeName)
                        return tpair.second;
                }
            }
        }
        else
        {
            auto it = Types.find(ContextName);
            if (it != Types.end())
            {
                auto t_it = it->second.find(TypeName);
                if (t_it != it->second.end())
                    return t_it->second;
            }
        }

        return DefaultObject;
    };

    void Initialize()
    {
        Types.empty();
    }
};