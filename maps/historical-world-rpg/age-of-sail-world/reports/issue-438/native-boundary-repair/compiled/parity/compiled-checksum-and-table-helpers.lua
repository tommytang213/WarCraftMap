function runtimeChecksum(value50, __wurst_stackPos920) 
	local wurst_stack_local184 = wurst_stack
	local result56 = nil
	local i365 = nil
	local temp374 = nil
	local character = nil
	local identity5 = nil
	local this2116 = nil
	local stackTrace_tempReturn176 = nil
	local this2117 = nil
	local value135 = nil
	local parentKey15 = nil
	local childKey12 = nil
	wurst_stack_local184[wurst_stack_depth] = __wurst_stackPos920
	wurst_stack_depth = (wurst_stack_depth + 1)
	if (PlayableCampaignRuntime_runtimeCharacterHashes == nil) then
		PlayableCampaignRuntime_runtimeCharacterHashes = Table_new_Table("when calling new_Table in PlayableCampaignRuntime, line 1069")
	end
	result56 = 5381
	i365 = 0
	temp374 = (StringLength(value50) - 1)
	while true do
		if (i365 > temp374) then
			break
		end
		character = SubString(value50, i365, (i365 + 1))
		identity5 = __wurst_stringToIndex(character)
		this2116 = PlayableCampaignRuntime_runtimeCharacterHashes
		value135 = identity5
		wurst_stack_local184[wurst_stack_depth] = "when calling hasInt in PlayableCampaignRuntime, line 1074"
		wurst_stack_depth = (wurst_stack_depth + 1)
		this2117 = Table_ht
		parentKey15 = __wurst_classToIndex(this2116)
		wurst_stack_local184[wurst_stack_depth] = "when calling hasInt in Table, line 11"
		wurst_stack_depth = (wurst_stack_depth + 1)
		stackTrace_tempReturn176 = __wurst_HaveSavedInteger(this2117, parentKey15, value135)
		wurst_stack_depth = ((wurst_stack_depth - 1) - 1)
		if not(stackTrace_tempReturn176) then
			this2116 = PlayableCampaignRuntime_runtimeCharacterHashes
			childKey12 = identity5
			value135 = StringHash(character)
			wurst_stack_local184[wurst_stack_depth] = "when calling saveInt in PlayableCampaignRuntime, line 1075"
			wurst_stack_depth = (wurst_stack_depth + 1)
			this2117 = Table_ht
			parentKey15 = __wurst_classToIndex(this2116)
			wurst_stack_local184[wurst_stack_depth] = "when calling saveInt in Table, line 44"
			wurst_stack_depth = (wurst_stack_depth + 1)
			__wurst_SaveInteger(this2117, parentKey15, childKey12, value135)
			wurst_stack_depth = ((wurst_stack_depth - 1) - 1)
		end
		result56 = (result56 * 33)
		this2116 = PlayableCampaignRuntime_runtimeCharacterHashes
		parentKey15 = identity5
		wurst_stack_local184[wurst_stack_depth] = "when calling loadInt in PlayableCampaignRuntime, line 1076"
		wurst_stack_depth = (wurst_stack_depth + 1)
		this2117 = Table_ht
		identity5 = __wurst_classToIndex(this2116)
		wurst_stack_local184[wurst_stack_depth] = "when calling loadInt in Table, line 41"
		wurst_stack_depth = (wurst_stack_depth + 1)
		identity5 = __wurst_LoadInteger(this2117, identity5, parentKey15)
		wurst_stack_depth = ((wurst_stack_depth - 1) - 1)
		parentKey15 = (result56 + identity5)
		result56 = parentKey15
		value135 = 2147483000
		childKey12 = (parentKey15 // 2147483000)
		if ((childKey12 < 0) and not(((childKey12 * 2147483000) == parentKey15))) then
			childKey12 = (childKey12 + 1)
		end
		result56 = (result56 - (childKey12 * 2147483000))
		if (result56 < 0) then
			result56 = (result56 + 2147483000)
		end
		i365 = (i365 + 1)
	end
	wurst_stack_depth = (wurst_stack_depth - 1)
	return result56
end

function __wurst_stringToIndex(x) 
	if x == nil then
	    return 0
	end
	if type(x) ~= "string" then
	    x = tostring(x)
	end
	local id = __wurst_string_index_map.byString[x]
	if id ~= nil then
	    return id
	end
	id = __wurst_string_index_map.counter + 1
	__wurst_string_index_map.counter = id
	__wurst_string_index_map.byString[x] = id
	__wurst_string_index_map.byIndex[id] = x
	return id
end

function __wurst_InitHashtable() 
	return { __wurst_ht_int = {}, __wurst_ht_bool = {}, __wurst_ht_real = {}, __wurst_ht_str = {}, __wurst_ht_handle = {} }
end

function __wurst_SaveInteger(h, p, c, i) 
	local t = h.__wurst_ht_int
	if t == nil then t = {}; h.__wurst_ht_int = t end
	if not t[p] then t[p] = {} end t[p][c] = i
end

function __wurst_LoadInteger(h, p, c) 
	local t = h.__wurst_ht_int
	if t == nil or t[p] == nil then return 0 end
	local v = t[p][c]
	if v == nil then return 0 end
	return v
end

function __wurst_HaveSavedInteger(h, p, c) 
	local t = h.__wurst_ht_int
	return t ~= nil and t[p] ~= nil and t[p][c] ~= nil
end
